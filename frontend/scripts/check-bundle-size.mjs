// F08-RT-05: o JS e o CSS carregados por `index.html` somam no máximo 250 kB em gzip.
// Roda depois de `npm run build` (script `postbuild`), no CI e no `make deploy-web`.
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { gzipSync } from 'node:zlib'

const LIMIT_KB = 250
const dist = new URL('../dist/', import.meta.url).pathname
const html = readFileSync(join(dist, 'index.html'), 'utf8')
const assets = [...html.matchAll(/(?:src|href)="\/?(assets\/[^"]+\.(?:js|css))"/g)].map((m) => m[1])

const sizes = assets.map((file) => ({
  file,
  kb: gzipSync(readFileSync(join(dist, file)), { level: 9 }).length / 1024,
}))
const total = sizes.reduce((sum, s) => sum + s.kb, 0)

for (const s of sizes) console.log(`  ${s.file}: ${s.kb.toFixed(1)} kB gzip`)
if (assets.length === 0 || total > LIMIT_KB) {
  console.error(`Bundle inicial com ${total.toFixed(1)} kB gzip; limite ${LIMIT_KB} kB (F08-RT-05)`)
  process.exit(1)
}
console.log(`ok: bundle inicial ${total.toFixed(1)} kB gzip (limite ${LIMIT_KB} kB)`)
