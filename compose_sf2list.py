import struct, sys
def presets(path):
    f = open(path, "rb"); data = f.read()
    i = data.find(b"phdr"); n = struct.unpack("<I", data[i + 4:i + 8])[0]; out = []
    for k in range(n // 38 - 1):
        rec = data[i + 8 + k * 38: i + 8 + (k + 1) * 38]
        name = rec[:20].split(b"\0")[0].decode("latin1"); prog, bank = struct.unpack("<HH", rec[20:24]); out.append((bank, prog, name))
    return sorted(out)
for p in sys.argv[1:]:
    ps = presets(p); print(p.split("/")[-1], len(ps))
    print("  " + " | ".join(f"{b}:{pr} {n}" for b, pr, n in ps if b != 0 or len(ps) < 80)[:3000])
