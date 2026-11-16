// F08-RT-08: o build de produção não pode levar os dados de demonstração (`src/product/demo.ts`).
// Roda depois de `npm run build` (script `postbuild`), inclusive no `make deploy-web`.
import { readdirSync, readFileSync } from 'node:fs'
import { join } from 'node:path'

const MARKERS = ['jira.example.com', 'PO de demonstração']
const dir = new URL('../dist/assets/', import.meta.url).pathname
const found = readdirSync(dir)
  .filter((f) => f.endsWith('.js'))
  .flatMap((f) => {
    const code = readFileSync(join(dir, f), 'utf8')
    return MARKERS.filter((m) => code.includes(m)).map((m) => `${f}: "${m}"`)
  })

if (found.length > 0) {
  console.error('Dados de demonstração no build de produção (F08-RT-08):\n' + found.join('\n'))
  process.exit(1)
}
console.log('ok: build sem dados de demonstração')
