#!/usr/bin/env python3
"""Split Sloppy's embedded Wasm from its HTML, avoiding a large base64 DOM/string.

Run after `sloppy build ... --target wasm -o site/index.html`. Upload both files.
The module remains byte-identical; upload both the loader and its hashed module.
"""
import argparse
import base64
import hashlib
from pathlib import Path
import re


def package(html: Path) -> Path:
    source = html.read_text()
    pattern = re.compile(r'^const SLOPPY_WASM = "([A-Za-z0-9+/=]+)";\n', re.MULTILINE)
    matches = list(pattern.finditer(source))
    if len(matches) != 1 or source.count('</body>') != 1:
        raise ValueError('Expected one Sloppy Wasm payload and one HTML body')
    match = matches[0]
    wasm = base64.b64decode(match.group(1), validate=True)
    if wasm[:8] != b'\x00asm\x01\x00\x00\x00':
        raise ValueError('Invalid Wasm module header')
    name = f'aegean.{hashlib.sha256(wasm).hexdigest()[:16]}.wasm'
    module = html.with_name(name)
    # The compiler's original bootstrap is guarded by typeof SLOPPY_WASM;
    # removing that declaration disables it. Keep the runtime itself unchanged.
    source = source[:match.start()] + source[match.end():]
    bootstrap = '''<script>
(() => {
  const fail = (e) => {
    const log = document.getElementById("log");
    log.style.display = "block";
    log.textContent += "error: " + sloppy.errorText(e) + "\\n";
  };
  window.addEventListener("error", ev => fail(ev.error || ev.message));
  window.addEventListener("load", async () => {
    try {
      const response = await fetch("MODULE_NAME");
      if (!response.ok) throw new Error("World download failed: " + response.status);
      await sloppy.run(new Uint8Array(await response.arrayBuffer()));
    } catch (e) { fail(e); }
  });
})();
</script>
'''.replace('MODULE_NAME', name)
    module.write_bytes(wasm)
    html.write_text(source.replace('</body>', bootstrap + '</body>'))
    print(f'{html.name}: {html.stat().st_size} bytes; {name}: {len(wasm)} bytes')
    return module


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('html', type=Path)
    package(parser.parse_args().html)
