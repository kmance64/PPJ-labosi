import sys

def main():
    lines = sys.stdin.readlines()

    broj_vrijednost = None

    for line in lines:
        line = line.strip()
        if line.startswith("BROJ"):
            broj_vrijednost = int(line.split()[2])
            break

    if broj_vrijednost is None:
        return

    with open("a.s", "w") as f:
        f.write(".text\n")
        f.write(".global _start\n\n")
        f.write("_start:\n")
        f.write(f"    MOV r6, #{broj_vrijednost}\n")
        f.write("    SVC #0\n")

if __name__ == "__main__":
    main()
