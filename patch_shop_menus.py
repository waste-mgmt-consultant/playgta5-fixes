"""Patch game.wasm so shop menus open although the 2014 data set lacks NG/MP menu assets.

The shop scripts wait for MPShopSale.ytd and the COLOUR_SWITCHER_01/02 scaleform movies,
which this data set (no update.rpf) does not contain, so the menu never opens.
- HAS_STREAMED_TEXTURE_DICT_LOADED: a dictionary that is not in the store reports loaded.
- REQUEST_SCALEFORM_MOVIE: a plain movie name that is not in the scaleform store returns MISSING_MOVIE (-50)
  before CreateMovie runs; CreateMovie would add a "non_str_<name>" slot for it that never loads.
  Every movie command rejects ids <= 0, and HAS_SCALEFORM_MOVIE_LOADED(MISSING_MOVIE) reports loaded
  (patched in the command and in the script native, which inlines its own copy).
  Id 0 keeps meaning "not requested", so scripts still request movies they have not asked for yet.
  Names with '/', '\\' or '.' skip the check: CreateMovie loads those from a path, not from the store.

Also a cash hotkey: each press of the key index.html maps to CASH_KEY_FLAG adds $999,999 to the current
character's SPn_TOTAL_CASH, through the same calls a money pickup makes (CPickupRewardMoneyFixed::Give).

Also a resource heap cap: sysMemGrowBuddyAllocator::GrowHeap adds a 256 MB heap whenever the free space is below 4 MB,
up to 32 heaps, so the streaming cache never evicts and grows until the 3 GB wasm memory is gone (a session crashed
with "Invalid fixup" at 1256/1280 MB). With at most GROW_HEAP_LIMIT heaps, GetMemoryAvailable reports the real free
space and strStreamingAllocator::MakeSpaceForAllocation deletes the least used objects instead.

Reads b/8b0b5899ed/game.wasm.orig (the untouched backup) and writes b/8b0b5899ed/game.wasm.
On the first run game.wasm is the untouched file: it is checked and copied to game.wasm.orig first.
Restore: cp game.wasm.orig game.wasm
"""
import hashlib, shutil, struct, sys
from pathlib import Path

DIR = Path(__file__).resolve().parent / 'mirror' / 'playgta5.com' / 'b' / '8b0b5899ed'
ORIG_SHA256 = '11ca8d2c04c5e843d18ff4aea4899d72c86973c6b031df334e67c446b2ae83e0'

# Body file offsets (wasm-objdump) of the functions, checked against their indices below.
HAS_TXD_LOADED = (50534, 0x1dc1382)          # graphics_commands::HasStreamedTxdLoaded
REQUEST_MOVIE = (50785, 0x1dc8e5f)           # graphics_commands::CommandRequestScaleformMovieCommon
HAS_MOVIE_LOADED = (50789, 0x1dc92c4)        # graphics_commands::CommandHasScaleformMovieLoaded
HAS_MOVIE_LOADED_NATIVE = (51266, 0x1dd6879) # scrWrapped_HAS_SCALEFORM_MOVIE_LOADED::Call (inlines the command)
STATS_UPDATE = (77092, 0x2647586)            # CStatsMgr::Update, once per game frame
GROW_HEAP = (3036, 0x264d27)                 # rage::sysMemGrowBuddyAllocator::GrowHeap
GROW_HEAP_LIMIT = 6                          # heaps of 256 MB: resource virtual stops at 1536 MB
# Each has an inlined CMovieMgr::CMovie::WaitTillLoaded: unless flags97 & 1, sleep until bwMovie byte 171 (loaded) is set.
# Only the AsyncBink thread sets it, and the wasm build never starts that thread (no Bink), so the main thread sleeps
# forever once a TV movie is deleted (Michael's TV in Armenian 3). 'and' -> 'or' makes the skip test always true.
MOVIE_WAITS = ((80969, 0x29996d6), (80987, 0x29a3c98), (81493, 0x29fbf85), (81494, 0x29fc348), (81507, 0x29fd2b2),
               (36164, 0x14905f6), (36283, 0x14af1e9))  # CMovieMgr: UpdateFrame, Delete, CMovie::Play, Stop, GetTime; CPauseMenu: Open, SetupCodeForUnPause
MOVIE_WAIT_TEST = bytes.fromhex('2d0061' '4101' '71' '45' '0440' '4285f004')  # load8_u 97; i32.const 1; and; eqz; if; i64.const 79877

# Cash hotkey. index.html sets CASH_KEY_FLAG once per press; CStatsMgr::Update consumes it.
CASH_KEY_FLAG = 6583436 + 0xE8   # in the engine's 256-byte keyboard block (wasm_input_test_key); VK 0xE8 is unassigned
CASH_STAT = 25469204             # StatId_char {SP0,SP1,SP2}_TOTAL_CASH (+ MP slots), set up in __wasm_call_ctors
CASH_AMOUNT = 999999.0           # IncrementStat takes a float; exact below 2**24
GET_STAT_ID, IS_KEY_VALID, INCREMENT_STAT = 77153, 77193, 77089  # StatId_char::GetStatId, CStatsDataMgr::IsKeyValid, CStatsMgr::IncrementStat


def asm(text):
    """Hex bytes, one instruction group per line; '#' starts a comment."""
    return bytes.fromhex(''.join(line.split('#')[0] for line in text.splitlines()).replace(' ', ''))


# HasStreamedTxdLoaded entry: the result (local 2) starts at 1, which every not-found path keeps.
TXD_ENTRY = asm('4101 2102')

# CommandRequestScaleformMovieCommon entry, before its stack frame. Locals 7, 8: i32, 9: i64 (new).
# The store's name map, as CScaleformMgr::CreateMovieInternal reads it: i32 size at 19601576, bucket
# array pointer at 19601568, entry array pointer at 19601560; entries are {hash, slot, next}, -1 ends a chain.
MOVIE_PRECHECK = asm('''
    0240                         # block $known
    2000 2109                    #   p = name
    0240 0340                    #   block, loop: scan the name
    2009 2d0000 2208 45 0d01     #     c = *p; end of string -> scan done
    2008 412f 46 0d02            #     '/' -> $known
    2008 412e 46 0d02            #     '.' -> $known
    2008 41dc00 46 0d02          #     '\\' -> $known
    2009 4201 7c 2109 0c00       #     p++
    0b 0b
    4101 2000 10a805 2107        #   hash = ComputeHash(1, name)   (func 680)
    42a8b1ac09 280200 2208       #   n = map size
    45 0d00                      #   empty map (store not set up) -> $known
    42a0b1ac09 290300 2007 2008 70 ad 4202 86 7c 280200 2108    # i = buckets[hash % n]
    0240 0340                    #   block, loop over the chain
    2008 417f 46 0d01            #     i == -1 -> not found
    4298b1ac09 290300 2008 ad 420c 7e 7c 2209                   # e = &entries[i]
    280200 2007 46 0440          #     if (e.hash == hash)
    2009 280204 417f 47 0d03     #       e.slot != -1 -> $known
    0c02 0b                      #       else not found
    2009 280208 2108 0c00        #     i = e.next
    0b 0b
    414e 0f                      #   return MISSING_MOVIE (-50)
    0b
''')
# CommandHasScaleformMovieLoaded entry: if (id == MISSING_MOVIE) return 1;
MOVIE_LOADED_CHECK = asm('2000 414e 46 0440 4101 0f 0b')
# The script native has its own inlined copy: if (args[0] == MISSING_MOVIE) { *result = 1; return; }
MOVIE_LOADED_NATIVE_CHECK = asm('''
    2000 290310 280200 414e 46 0440    # info.args[0] == MISSING_MOVIE
    2000 290300 4101 360200 0f         #   *info.result = 1; return
    0b
''')


def leb(data, i):
    result = shift = 0
    while True:
        byte = data[i]; i += 1
        result |= (byte & 0x7f) << shift; shift += 7
        if byte < 0x80:
            return result, i


def enc_leb(value):
    out = bytearray()
    while True:
        byte = value & 0x7f; value >>= 7
        out.append(byte | (0x80 if value else 0))
        if not value:
            return bytes(out)


def sleb(value):
    out = bytearray()
    while True:
        byte = value & 0x7f; value >>= 7
        if (value == 0 and not byte & 0x40) or (value == -1 and byte & 0x40):
            return bytes(out + bytes([byte]))
        out.append(byte | 0x80)


def cash_hotkey():
    """CStatsMgr::Update entry: if (flag) { flag = 0; id = CASH.GetStatId(); if (IsKeyValid(id)) IncrementStat(id, amount, 3); }"""
    i64 = lambda v: (b'\x42' + sleb(v)).hex()
    call = lambda f: (b'\x10' + enc_leb(f)).hex()
    return asm(f'''
        {i64(CASH_KEY_FLAG)} 2d0000 0440                       # if (flag)
        {i64(CASH_KEY_FLAG)} 4100 3a0000                       #   flag = 0
        2300 4210 7d 2400                                      #   sp -= 16
        2300 4208 7c {i64(CASH_STAT)} {call(GET_STAT_ID)}      #   id (at sp + 8) = the current character's cash stat
        2300 4208 7c {call(IS_KEY_VALID)} 0440                 #   if (IsKeyValid(id))
        2300 4208 7c 43{struct.pack('<f', CASH_AMOUNT).hex()} 4103 {call(INCREMENT_STAT)}
        0b
        2300 4210 7c 2400                                      #   sp += 16
        0b
    ''')


def locals_end(body):
    count, i = leb(body, 0)
    for _ in range(count):
        _, i = leb(body, i)
        i += 1
    return i


def check(ok, what):
    if not ok:
        sys.exit(f'{what} does not match; not the expected game.wasm, nothing written')


def patch(data):
    i = 8
    while data[i] != 10:
        size, j = leb(data, i + 1)
        i = j + size
    section_start = i
    section_size, j = leb(data, i + 1)
    section_end = j + section_size
    count, p = leb(data, j)
    bodies, starts = [], {}
    while p < section_end:
        size, q = leb(data, p)
        starts[q] = len(bodies)
        bodies.append(bytearray(data[q:q + size]))
        p = q + size
    check(len(bodies) == count and HAS_TXD_LOADED[1] in starts, 'code section')

    first_index = HAS_TXD_LOADED[0] - starts[HAS_TXD_LOADED[1]]
    for index, offset in (REQUEST_MOVIE, HAS_MOVIE_LOADED, HAS_MOVIE_LOADED_NATIVE, STATS_UPDATE, GROW_HEAP):
        check(starts.get(offset, -1) + first_index == index, f'func[{index}] offset')
    body = lambda fn: bodies[fn[0] - first_index]

    txd = body(HAS_TXD_LOADED)
    check(txd[:5] == bytes.fromhex('02037f017e'), 'HasStreamedTxdLoaded locals')
    check(txd[5:14] == bytes.fromhex('41004100200010a805'), 'HasStreamedTxdLoaded entry')
    txd[5:5] = TXD_ENTRY

    req = body(REQUEST_MOVIE)
    check(req[:5] == bytes.fromhex('02037e017f'), 'CommandRequestScaleformMovieCommon locals')
    check(req[5:15] == bytes.fromhex('230042a0017d22032400'), 'CommandRequestScaleformMovieCommon frame')
    req[:5] = bytes.fromhex('03037e037f017e') + MOVIE_PRECHECK  # + locals 7, 8: i32, 9: i64

    has = body(HAS_MOVIE_LOADED); at = locals_end(has)
    check(has[at:at + 7] == bytes.fromhex('0240200041016b'), 'HasScaleformMovieLoaded entry')
    has[at:at] = MOVIE_LOADED_CHECK

    native = body(HAS_MOVIE_LOADED_NATIVE); at = locals_end(native)
    check(native[at:at + 8] == bytes.fromhex('0240200029031028'), 'HAS_SCALEFORM_MOVIE_LOADED native entry')
    native[at:at] = MOVIE_LOADED_NATIVE_CHECK

    stats = body(STATS_UPDATE); at = locals_end(stats)
    check(stats[at:at + 9] == bytes.fromhex('230042407c22052400'), 'CStatsMgr::Update entry')
    stats[at:at] = cash_hotkey()

    # GrowHeap entry: if (heapCount <= 31) grow; the constant becomes GROW_HEAP_LIMIT - 1 (same 1-byte LEB).
    grow = body(GROW_HEAP); at = locals_end(grow)
    check(grow[at:at + 13] == bytes.fromhex('024020002802fc032210411f4d'), 'GrowHeap entry')
    grow[at + 11] = GROW_HEAP_LIMIT - 1

    for fn in MOVIE_WAITS:
        check(starts.get(fn[1], -1) + first_index == fn[0], f'func[{fn[0]}] offset')
        movie = body(fn); at = movie.find(MOVIE_WAIT_TEST)
        check(at >= 0 and movie.count(MOVIE_WAIT_TEST) == 1, f'func[{fn[0]}] WaitTillLoaded test')
        movie[at + 5] = 0x72  # i32.or

    payload = enc_leb(count) + b''.join(enc_leb(len(b)) + b for b in bodies)
    section = bytes([10]) + enc_leb(len(payload)) + payload
    return data[:section_start] + section + data[section_end:]


if __name__ == '__main__':
    orig = DIR / 'game.wasm.orig'
    if not orig.exists():
        check(hashlib.sha256((DIR / 'game.wasm').read_bytes()).hexdigest() == ORIG_SHA256, 'game.wasm sha256')
        shutil.copy2(DIR / 'game.wasm', orig)
    source = orig.read_bytes()
    check(hashlib.sha256(source).hexdigest() == ORIG_SHA256, 'game.wasm.orig sha256')
    patched = patch(source)
    (DIR / 'game.wasm').write_bytes(patched)
    print(f'game.wasm patched: {len(source)} -> {len(patched)} bytes, sha256 {hashlib.sha256(patched).hexdigest()}')
