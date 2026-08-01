<template>
  <header class="workflow-header">
    <button class="workflow-brand" type="button" aria-label="Return to MiroFish home" @click="$emit('home')">
      <span class="workflow-brand-mark" aria-hidden="true">MF</span>
      <span>MiroFish</span>
    </button>

    <div class="view-switcher" aria-label="Workspace layout">
      <button
        v-for="mode in modes"
        :key="mode.key"
        class="switch-btn"
        :class="{ active: viewMode === mode.key }"
        type="button"
        :aria-pressed="viewMode === mode.key"
        @click="$emit('change-view', mode.key)"
      >
        {{ mode.label }}
      </button>
    </div>

    <div class="workflow-context">
      <div class="workflow-progress" aria-label="Workflow progress">
        <span class="step-count">{{ paddedStep }} / 05</span>
        <span class="step-name">{{ stepName }}</span>
      </div>
      <span class="status-indicator" :class="statusClass">
        <span class="dot" aria-hidden="true"></span>
        {{ statusText }}
      </span>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  step: { type: Number, required: true },
  stepName: { type: String, required: true },
  statusText: { type: String, required: true },
  statusClass: { type: String, default: '' },
  viewMode: { type: String, default: 'split' }
})

defineEmits(['home', 'change-view'])

const modes = [
  { key: 'graph', label: 'Graph' },
  { key: 'split', label: 'Split' },
  { key: 'workbench', label: 'Workbench' }
]

const paddedStep = computed(() => String(props.step).padStart(2, '0'))
</script>

<style scoped>
.workflow-header {
  position: relative;
  z-index: 20;
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  min-height: 72px;
  padding: 0 22px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.2);
  background: rgba(10, 22, 35, 0.94);
  box-shadow: 0 10px 35px rgba(7, 19, 31, 0.18);
  backdrop-filter: blur(18px);
}

.workflow-brand {
  display: inline-flex;
  align-items: center;
  justify-self: start;
  gap: 10px;
  border: 0;
  color: #f5f8fb;
  background: transparent;
  font-family: var(--font-display);
  font-size: 0.94rem;
  font-weight: 750;
  cursor: pointer;
}

.workflow-brand-mark {
  display: grid;
  width: 32px;
  height: 32px;
  place-items: center;
  border-radius: 10px;
  color: #07131f;
  background: var(--accent);
  font-family: var(--font-mono);
  font-size: 0.66rem;
  font-weight: 900;
}

.view-switcher {
  display: flex;
  gap: 3px;
  padding: 4px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.045);
}

.switch-btn {
  padding: 8px 13px;
  border: 0;
  border-radius: 8px;
  color: #899aad;
  background: transparent;
  font-family: var(--font-mono);
  font-size: 0.65rem;
  font-weight: 750;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  cursor: pointer;
}

.switch-btn:hover {
  color: #eef3f8;
}

.switch-btn.active {
  color: #091522;
  background: var(--accent);
}

.workflow-context {
  display: flex;
  align-items: center;
  justify-self: end;
  gap: 20px;
}

.workflow-progress {
  display: grid;
  grid-template-columns: auto auto;
  gap: 4px 10px;
  align-items: baseline;
}

.step-count {
  color: var(--accent);
  font-family: var(--font-mono);
  font-size: 0.66rem;
  font-weight: 800;
}

.step-name {
  color: #e7edf3;
  font-size: 0.78rem;
  font-weight: 700;
}

.status-indicator {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 7px 10px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 999px;
  color: #9baabb;
  font-family: var(--font-mono);
  font-size: 0.62rem;
  font-weight: 700;
  text-transform: uppercase;
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #f5b544;
  box-shadow: 0 0 0 3px rgba(245, 181, 68, 0.13);
}

.status-indicator.completed .dot,
.status-indicator.ready .dot {
  background: var(--accent);
  box-shadow: 0 0 0 3px rgba(73, 222, 177, 0.13);
}

.status-indicator.error .dot {
  background: #ff776d;
  box-shadow: 0 0 0 3px rgba(255, 119, 109, 0.13);
}

@media (max-width: 860px) {
  .workflow-header {
    grid-template-columns: auto 1fr;
    gap: 12px;
    padding: 12px 14px;
  }

  .view-switcher {
    grid-column: 1 / -1;
    grid-row: 2;
    justify-self: stretch;
  }

  .switch-btn {
    flex: 1;
  }

  .workflow-context {
    gap: 10px;
  }

  .step-name {
    display: none;
  }
}
</style>
