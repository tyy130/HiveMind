<template>
  <div class="home-shell">
    <nav class="site-nav" aria-label="Primary navigation">
      <button class="brand-lockup" type="button" @click="scrollToTop">
        <span class="brand-mark" aria-hidden="true">MF</span>
        <span>
          <strong>MiroFish</strong>
          <small>Collective intelligence engine</small>
        </span>
      </button>

      <div class="nav-actions">
        <span class="system-status"><i></i> System online</span>
        <a
          class="nav-link"
          href="https://github.com/666ghj/MiroFish"
          target="_blank"
          rel="noopener noreferrer"
        >
          View source <span aria-hidden="true">↗</span>
        </a>
      </div>
    </nav>

    <main>
      <section class="hero-grid">
        <div class="hero-copy">
          <div class="eyebrow"><span>Preview 0.1</span> Agent-based forecasting</div>
          <h1>Run the world<br><em>before it happens.</em></h1>
          <p class="hero-lede">
            Turn source material into a living simulation. MiroFish builds a knowledge graph,
            generates agent populations, and lets you test how narratives evolve before decisions are made.
          </p>

          <div class="hero-actions">
            <button class="primary-action" type="button" @click="focusBrief">
              Start a simulation <span aria-hidden="true">→</span>
            </button>
            <button class="text-action" type="button" @click="scrollToWorkflow">
              See how it works
            </button>
          </div>

          <dl class="proof-grid">
            <div>
              <dt>01</dt>
              <dd>Grounded in your source material</dd>
            </div>
            <div>
              <dt>02</dt>
              <dd>Agents evolve across social environments</dd>
            </div>
            <div>
              <dt>03</dt>
              <dd>Reports stay traceable to the graph</dd>
            </div>
          </dl>
        </div>

        <aside id="simulation-brief" class="brief-card" aria-labelledby="brief-title">
          <div class="brief-card-header">
            <div>
              <span class="section-kicker">New run</span>
              <h2 id="brief-title">Build your simulation brief</h2>
            </div>
            <span class="step-chip">Step 1 of 5</span>
          </div>

          <div
            class="upload-panel"
            :class="{ active: isDragOver, populated: files.length > 0 }"
            @dragover.prevent="handleDragOver"
            @dragleave.prevent="handleDragLeave"
            @drop.prevent="handleDrop"
            @click="triggerFileInput"
          >
            <input
              ref="fileInput"
              class="visually-hidden-input"
              type="file"
              multiple
              accept=".pdf,.md,.txt"
              :disabled="loading"
              aria-label="Upload PDF, Markdown, or text files"
              @change="handleFileSelect"
              @click.stop
            />

            <div v-if="files.length === 0" class="upload-empty">
              <span class="upload-icon" aria-hidden="true">↑</span>
              <div>
                <strong>Drop your source files here</strong>
                <span>PDF, Markdown, or TXT — click to browse</span>
              </div>
            </div>

            <div v-else class="file-stack">
              <div class="file-stack-header">
                <span>{{ files.length }} {{ files.length === 1 ? 'source' : 'sources' }} ready</span>
                <button type="button" @click.stop="triggerFileInput">Add more</button>
              </div>
              <div v-for="file in files" :key="`${file.name}-${file.size}`" class="file-row">
                <span class="file-type" aria-hidden="true">{{ fileExtension(file.name) }}</span>
                <span class="file-meta">
                  <strong>{{ file.name }}</strong>
                  <small>{{ formatFileSize(file.size) }}</small>
                </span>
                <button
                  class="remove-file"
                  type="button"
                  :aria-label="`Remove ${file.name}`"
                  @click.stop="removeFile(file)"
                >
                  ×
                </button>
              </div>
            </div>
          </div>

          <label class="prompt-field">
            <span>
              <strong>What do you want to understand?</strong>
              <small>Be specific about the decision, audience, and time horizon.</small>
            </span>
            <textarea
              ref="promptInput"
              v-model="formData.simulationRequirement"
              rows="6"
              :disabled="loading"
              placeholder="Example: How would customers respond over the next 30 days if we changed our pricing model?"
            ></textarea>
          </label>

          <p v-if="error" class="form-error" role="alert">{{ error }}</p>

          <button
            class="launch-button"
            type="button"
            :disabled="!canSubmit || loading"
            @click="startSimulation"
          >
            <span>{{ loading ? 'Preparing workspace…' : 'Create simulation' }}</span>
            <span aria-hidden="true">→</span>
          </button>

          <p class="brief-note">Your files stay attached to this local simulation workflow.</p>
        </aside>
      </section>

      <section id="workflow" class="workflow-section" aria-labelledby="workflow-title">
        <div class="section-heading">
          <div>
            <span class="section-kicker">From evidence to action</span>
            <h2 id="workflow-title">One continuous forecasting workflow.</h2>
          </div>
          <p>Each stage builds on the last, so every insight can be traced back to source evidence.</p>
        </div>

        <ol class="workflow-grid">
          <li v-for="step in workflowSteps" :key="step.number">
            <span class="workflow-number">{{ step.number }}</span>
            <div>
              <h3>{{ step.title }}</h3>
              <p>{{ step.description }}</p>
            </div>
            <span class="workflow-arrow" aria-hidden="true">↗</span>
          </li>
        </ol>
      </section>

      <section class="history-wrap" aria-labelledby="history-title">
        <div class="section-heading compact">
          <div>
            <span class="section-kicker">Continue exploring</span>
            <h2 id="history-title">Recent simulations</h2>
          </div>
          <p>Return to a graph, simulation, report, or agent conversation without losing context.</p>
        </div>
        <HistoryDatabase />
      </section>
    </main>

    <footer class="site-footer">
      <span>MiroFish — Collective intelligence for consequential decisions</span>
      <span>Five stages. One evidence trail.</span>
    </footer>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import HistoryDatabase from '../components/HistoryDatabase.vue'
import { setPendingUpload } from '../store/pendingUpload.js'

const router = useRouter()
const fileInput = ref(null)
const promptInput = ref(null)
const files = ref([])
const loading = ref(false)
const error = ref('')
const isDragOver = ref(false)
const formData = ref({ simulationRequirement: '' })

const workflowSteps = [
  { number: '01', title: 'Build the graph', description: 'Extract entities, relationships, and evidence from your source material.' },
  { number: '02', title: 'Configure the world', description: 'Generate agent profiles, environments, and simulation constraints.' },
  { number: '03', title: 'Run the simulation', description: 'Watch agents act, react, and reshape the narrative over time.' },
  { number: '04', title: 'Read the signal', description: 'Synthesize outcomes into a structured, evidence-backed report.' },
  { number: '05', title: 'Interrogate the result', description: 'Talk with simulated agents and probe the report from any angle.' }
]

const canSubmit = computed(() => (
  formData.value.simulationRequirement.trim().length > 0 && files.value.length > 0
))

const fileExtension = name => name.split('.').pop()?.toUpperCase() || 'FILE'

const formatFileSize = (size) => {
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${Math.round(size / 1024)} KB`
  return `${(size / (1024 * 1024)).toFixed(1)} MB`
}

const scrollToTop = () => window.scrollTo({ top: 0, behavior: 'smooth' })
const scrollToWorkflow = () => document.querySelector('#workflow')?.scrollIntoView({ behavior: 'smooth' })

const focusBrief = () => {
  document.querySelector('#simulation-brief')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  window.setTimeout(() => promptInput.value?.focus(), 500)
}

const triggerFileInput = () => {
  if (!loading.value) fileInput.value?.click()
}

const addFiles = (incomingFiles) => {
  const accepted = []
  const rejected = []

  for (const file of incomingFiles) {
    const extension = file.name.split('.').pop()?.toLowerCase()
    if (['pdf', 'md', 'txt'].includes(extension)) accepted.push(file)
    else rejected.push(file.name)
  }

  const existing = new Set(files.value.map(file => `${file.name}-${file.size}`))
  files.value.push(...accepted.filter(file => !existing.has(`${file.name}-${file.size}`)))
  error.value = rejected.length > 0
    ? `Unsupported file type: ${rejected.join(', ')}. Use PDF, Markdown, or TXT.`
    : ''
}

const handleFileSelect = (event) => {
  addFiles(Array.from(event.target.files || []))
  event.target.value = ''
}

const handleDragOver = () => {
  if (!loading.value) isDragOver.value = true
}

const handleDragLeave = () => {
  isDragOver.value = false
}

const handleDrop = (event) => {
  isDragOver.value = false
  if (!loading.value) addFiles(Array.from(event.dataTransfer.files || []))
}

const removeFile = (target) => {
  files.value = files.value.filter(file => file !== target)
}

const startSimulation = async () => {
  if (!canSubmit.value || loading.value) return

  loading.value = true
  error.value = ''
  setPendingUpload(files.value, formData.value.simulationRequirement.trim())

  try {
    await router.push({ name: 'Process', params: { projectId: 'new' } })
  } catch (err) {
    error.value = err?.message || 'Unable to open the simulation workspace.'
    loading.value = false
  }
}
</script>

<style scoped>
.home-shell {
  min-height: 100vh;
  color: var(--ink-950);
  background:
    radial-gradient(circle at 82% 8%, rgba(73, 222, 177, 0.16), transparent 28rem),
    radial-gradient(circle at 8% 22%, rgba(93, 135, 255, 0.12), transparent 26rem),
    var(--surface-0);
}

.site-nav {
  position: sticky;
  top: 0;
  z-index: 30;
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: min(1440px, calc(100% - 48px));
  margin: 0 auto;
  padding: 18px 0;
  border-bottom: 1px solid rgba(16, 27, 45, 0.1);
  background: rgba(247, 249, 252, 0.84);
  backdrop-filter: blur(18px);
}

.brand-lockup {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  border: 0;
  background: transparent;
  color: inherit;
  text-align: left;
  cursor: pointer;
}

.brand-lockup strong,
.brand-lockup small {
  display: block;
}

.brand-lockup strong {
  font-family: var(--font-display);
  font-size: 1rem;
  letter-spacing: -0.02em;
}

.brand-lockup small {
  margin-top: 1px;
  color: var(--ink-500);
  font-size: 0.68rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.brand-mark {
  display: grid;
  width: 38px;
  height: 38px;
  place-items: center;
  border-radius: 12px;
  color: #07131f;
  background: var(--accent);
  font-family: var(--font-mono);
  font-size: 0.78rem;
  font-weight: 800;
}

.nav-actions,
.hero-actions,
.file-stack-header {
  display: flex;
  align-items: center;
}

.nav-actions {
  gap: 24px;
}

.system-status {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--ink-600);
  font-family: var(--font-mono);
  font-size: 0.72rem;
  text-transform: uppercase;
}

.system-status i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #24b47e;
  box-shadow: 0 0 0 4px rgba(36, 180, 126, 0.12);
}

.nav-link {
  color: var(--ink-900);
  font-size: 0.84rem;
  font-weight: 700;
  text-decoration: none;
}

.hero-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.03fr) minmax(420px, 0.72fr);
  gap: clamp(48px, 7vw, 112px);
  align-items: center;
  width: min(1320px, calc(100% - 48px));
  min-height: calc(100vh - 75px);
  margin: 0 auto;
  padding: 72px 0 88px;
}

.hero-copy {
  max-width: 760px;
}

.eyebrow,
.section-kicker {
  font-family: var(--font-mono);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.eyebrow {
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--ink-500);
}

.eyebrow span {
  padding: 7px 10px;
  border: 1px solid rgba(16, 27, 45, 0.14);
  border-radius: 999px;
  color: var(--ink-800);
  background: rgba(255, 255, 255, 0.74);
}

h1 {
  margin: 28px 0 26px;
  font-family: var(--font-display);
  font-size: clamp(4.2rem, 7.5vw, 7.8rem);
  font-weight: 620;
  letter-spacing: -0.075em;
  line-height: 0.87;
}

h1 em {
  color: var(--ink-400);
  font-style: normal;
}

.hero-lede {
  max-width: 680px;
  color: var(--ink-600);
  font-size: clamp(1.02rem, 1.4vw, 1.24rem);
  line-height: 1.72;
}

.hero-actions {
  gap: 22px;
  margin: 36px 0 56px;
}

.primary-action,
.launch-button {
  display: inline-flex;
  align-items: center;
  justify-content: space-between;
  border: 0;
  color: #f8fbff;
  background: var(--ink-950);
  font-weight: 750;
  cursor: pointer;
  box-shadow: 0 16px 30px rgba(8, 19, 31, 0.16);
}

.primary-action {
  gap: 28px;
  min-width: 222px;
  padding: 16px 18px;
  border-radius: 14px;
}

.primary-action:hover,
.launch-button:hover:not(:disabled) {
  transform: translateY(-2px);
  background: #16283b;
}

.text-action {
  border: 0;
  border-bottom: 1px solid var(--ink-300);
  background: transparent;
  color: var(--ink-700);
  font-weight: 700;
  cursor: pointer;
}

.proof-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin: 0;
}

.proof-grid div {
  padding-top: 16px;
  border-top: 1px solid rgba(16, 27, 45, 0.14);
}

.proof-grid dt {
  color: var(--accent-strong);
  font-family: var(--font-mono);
  font-size: 0.72rem;
  font-weight: 800;
}

.proof-grid dd {
  margin: 8px 0 0;
  color: var(--ink-600);
  font-size: 0.82rem;
  line-height: 1.45;
}

.brief-card {
  position: relative;
  padding: 26px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 26px;
  color: #ecf2f8;
  background:
    linear-gradient(145deg, rgba(255, 255, 255, 0.07), transparent 45%),
    #0b1826;
  box-shadow: 0 34px 90px rgba(16, 27, 45, 0.24);
}

.brief-card::after {
  position: absolute;
  right: -80px;
  bottom: -100px;
  width: 260px;
  height: 260px;
  border-radius: 50%;
  background: rgba(73, 222, 177, 0.12);
  content: '';
  filter: blur(12px);
  pointer-events: none;
}

.brief-card-header,
.section-heading {
  display: flex;
  justify-content: space-between;
  gap: 28px;
}

.brief-card-header {
  align-items: flex-start;
  margin-bottom: 22px;
}

.section-kicker {
  color: var(--accent);
}

.brief-card h2 {
  margin: 6px 0 0;
  font-family: var(--font-display);
  font-size: 1.55rem;
  letter-spacing: -0.035em;
}

.step-chip {
  flex: 0 0 auto;
  padding: 7px 9px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 999px;
  color: #a7b5c3;
  font-family: var(--font-mono);
  font-size: 0.66rem;
}

.upload-panel {
  position: relative;
  min-height: 108px;
  padding: 16px;
  border: 1px dashed rgba(255, 255, 255, 0.22);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.035);
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
}

.upload-panel:hover,
.upload-panel.active,
.upload-panel:focus-within {
  border-color: var(--accent);
  background: rgba(73, 222, 177, 0.07);
}

.visually-hidden-input {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.upload-empty {
  display: flex;
  align-items: center;
  gap: 14px;
  min-height: 74px;
}

.upload-icon {
  display: grid;
  width: 46px;
  height: 46px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 13px;
  color: #07131f;
  background: var(--accent);
  font-size: 1.35rem;
}

.upload-empty strong,
.upload-empty span,
.prompt-field strong,
.prompt-field small {
  display: block;
}

.upload-empty strong {
  font-size: 0.92rem;
}

.upload-empty div > span,
.prompt-field small,
.brief-note {
  color: #94a5b7;
  font-size: 0.72rem;
}

.upload-empty div > span {
  margin-top: 5px;
}

.file-stack-header {
  justify-content: space-between;
  margin-bottom: 10px;
  color: #a8b6c4;
  font-family: var(--font-mono);
  font-size: 0.68rem;
  text-transform: uppercase;
}

.file-stack-header button {
  border: 0;
  color: var(--accent);
  background: transparent;
  font-size: 0.72rem;
  font-weight: 700;
  cursor: pointer;
}

.file-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 0;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.file-type {
  width: 34px;
  color: var(--accent);
  font-family: var(--font-mono);
  font-size: 0.62rem;
  font-weight: 800;
}

.file-meta {
  min-width: 0;
  flex: 1;
}

.file-meta strong,
.file-meta small {
  display: block;
}

.file-meta strong {
  overflow: hidden;
  font-size: 0.78rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-meta small {
  margin-top: 2px;
  color: #8293a5;
  font-size: 0.66rem;
}

.remove-file {
  width: 30px;
  height: 30px;
  border: 0;
  border-radius: 9px;
  color: #b5c1cd;
  background: rgba(255, 255, 255, 0.06);
  cursor: pointer;
}

.prompt-field {
  display: block;
  margin-top: 18px;
}

.prompt-field > span {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 9px;
}

.prompt-field strong {
  font-size: 0.84rem;
}

.prompt-field textarea {
  width: 100%;
  min-height: 132px;
  padding: 14px;
  resize: vertical;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 14px;
  outline: none;
  color: #f4f7fa;
  background: rgba(255, 255, 255, 0.055);
  font: 0.84rem/1.55 var(--font-sans);
}

.prompt-field textarea:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(73, 222, 177, 0.1);
}

.prompt-field textarea::placeholder {
  color: #728396;
}

.form-error {
  margin: 12px 0 0;
  color: #ffb4ac;
  font-size: 0.76rem;
}

.launch-button {
  position: relative;
  z-index: 1;
  width: 100%;
  margin-top: 16px;
  padding: 16px;
  border-radius: 14px;
  color: #07131f;
  background: var(--accent);
  box-shadow: none;
}

.launch-button:disabled {
  color: #718092;
  background: #233243;
  cursor: not-allowed;
}

.brief-note {
  position: relative;
  z-index: 1;
  margin: 10px 0 0;
  text-align: center;
}

.workflow-section,
.history-wrap {
  width: min(1320px, calc(100% - 48px));
  margin: 0 auto;
  padding: 110px 0;
}

.workflow-section {
  border-top: 1px solid rgba(16, 27, 45, 0.1);
}

.section-heading {
  align-items: flex-end;
  margin-bottom: 44px;
}

.section-heading h2 {
  max-width: 760px;
  margin: 8px 0 0;
  font-family: var(--font-display);
  font-size: clamp(2.6rem, 5vw, 4.8rem);
  letter-spacing: -0.06em;
  line-height: 0.98;
}

.section-heading > p {
  max-width: 390px;
  margin: 0;
  color: var(--ink-500);
  line-height: 1.6;
}

.workflow-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 10px;
  padding: 0;
  list-style: none;
}

.workflow-grid li {
  position: relative;
  min-height: 230px;
  padding: 20px;
  border: 1px solid rgba(16, 27, 45, 0.1);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.64);
  transition: transform 0.2s, border-color 0.2s, box-shadow 0.2s;
}

.workflow-grid li:hover {
  z-index: 2;
  transform: translateY(-5px);
  border-color: rgba(16, 27, 45, 0.2);
  box-shadow: 0 18px 40px rgba(16, 27, 45, 0.09);
}

.workflow-number {
  color: var(--accent-strong);
  font-family: var(--font-mono);
  font-size: 0.7rem;
  font-weight: 800;
}

.workflow-grid h3 {
  margin: 70px 0 10px;
  font-family: var(--font-display);
  font-size: 1.25rem;
  letter-spacing: -0.035em;
}

.workflow-grid p {
  margin: 0;
  color: var(--ink-500);
  font-size: 0.78rem;
  line-height: 1.55;
}

.workflow-arrow {
  position: absolute;
  top: 18px;
  right: 18px;
  color: var(--ink-300);
}

.history-wrap {
  padding-top: 30px;
}

.section-heading.compact h2 {
  font-size: clamp(2.4rem, 4vw, 3.8rem);
}

.site-footer {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  width: min(1320px, calc(100% - 48px));
  margin: 0 auto;
  padding: 24px 0 40px;
  border-top: 1px solid rgba(16, 27, 45, 0.1);
  color: var(--ink-400);
  font-family: var(--font-mono);
  font-size: 0.68rem;
}

@media (max-width: 1100px) {
  .hero-grid {
    grid-template-columns: 1fr;
    gap: 56px;
    padding-top: 76px;
  }

  .hero-copy {
    max-width: none;
  }

  .brief-card {
    width: min(680px, 100%);
  }

  .workflow-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 720px) {
  .site-nav,
  .hero-grid,
  .workflow-section,
  .history-wrap,
  .site-footer {
    width: min(100% - 28px, 1320px);
  }

  .site-nav {
    padding: 13px 0;
  }

  .brand-lockup small,
  .system-status {
    display: none;
  }

  .nav-actions {
    gap: 12px;
  }

  .hero-grid {
    min-height: auto;
    padding: 58px 0 70px;
  }

  h1 {
    font-size: clamp(3.5rem, 16vw, 5.3rem);
  }

  .hero-actions,
  .section-heading,
  .prompt-field > span,
  .site-footer {
    align-items: flex-start;
    flex-direction: column;
  }

  .proof-grid,
  .workflow-grid {
    grid-template-columns: 1fr;
  }

  .brief-card {
    padding: 20px;
    border-radius: 20px;
  }

  .prompt-field small {
    margin-top: 4px;
  }

  .workflow-section,
  .history-wrap {
    padding: 80px 0;
  }

  .workflow-grid li {
    min-height: 180px;
  }

  .workflow-grid h3 {
    margin-top: 45px;
  }
}
</style>
