import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync, readdirSync } from 'node:fs'
import { extname, join, relative } from 'node:path'
import { fileURLToPath } from 'node:url'

const frontendRoot = fileURLToPath(new URL('../', import.meta.url))
const repositoryRoot = fileURLToPath(new URL('../../', import.meta.url))
const sourceRoots = [
  join(frontendRoot, 'src'),
  join(frontendRoot, 'index.html'),
  join(repositoryRoot, 'locales')
]
const textExtensions = new Set(['.css', '.html', '.js', '.json', '.vue'])
const hanUnicode = /[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\u3000-\u303f\uff00-\uffef]/u

function collectTextFiles(path) {
  if (extname(path)) return textExtensions.has(extname(path)) ? [path] : []

  return readdirSync(path, { withFileTypes: true }).flatMap(entry => {
    const entryPath = join(path, entry.name)
    return entry.isDirectory() ? collectTextFiles(entryPath) : collectTextFiles(entryPath)
  })
}

test('frontend source, locale files, and tracked-facing paths contain no Han Unicode', () => {
  const violations = []

  for (const file of sourceRoots.flatMap(collectTextFiles)) {
    const relativePath = relative(repositoryRoot, file)
    if (hanUnicode.test(relativePath) || hanUnicode.test(readFileSync(file, 'utf8'))) {
      violations.push(relativePath)
    }
  }

  assert.deepEqual(violations, [])
})

test('English is the only advertised locale', () => {
  const languages = JSON.parse(readFileSync(join(repositoryRoot, 'locales/languages.json'), 'utf8'))
  assert.deepEqual(Object.keys(languages), ['en'])
})

test('Step 4 uses the tested report parser module', () => {
  const reportSource = readFileSync(join(frontendRoot, 'src/components/Step4Report.vue'), 'utf8')
  assert.match(reportSource, /from '\.\.\/utils\/reportParsers\.js'/)
  assert.match(reportSource, /parseInsightForgeContract\(log\.details\.result\)/)
  assert.match(reportSource, /parsePanoramaContract\(log\.details\.result\)/)
  assert.match(reportSource, /parseInterviewContract\(log\.details\.result\)/)
  assert.match(reportSource, /parseQuickSearchContract\(log\.details\.result\)/)
})
