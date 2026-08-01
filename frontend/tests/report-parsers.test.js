import test from 'node:test'
import assert from 'node:assert/strict'

import {
  parseInsightForge,
  parseInterview,
  parsePanorama,
  parseQuickSearch
} from '../src/utils/reportParsers.js'

const insightForgeOutput = `## Insight Forge
### Analysis Question
Will Orion Labs expand its energy-storage partnership?
### Prediction Scenario
Forecast the partnership through the next two quarters.

### Forecast Statistics
- Relevant prediction facts: 2
- Involved entities: 2
- Relationship chains: 1

### Analysis Questions
1. What capacity has been announced?
2. Which suppliers are exposed?

### Key Facts
1. "Orion Labs reserved additional battery capacity."
2. "Delta Grid approved a pilot expansion."

### Core Entities
- **Orion Labs** (Company)
  Summary: "A storage technology company."
  Relevant facts: 2

### Relationship Chains
- Orion Labs --[SUPPLIES]--> Delta Grid`

const panoramaOutput = `## Panorama Search
### Search Query
Orion Labs storage partnership

### Statistics
- Total number of nodes: 3
- Total number of edges: 2
- Currently valid facts: 2
- Historical or expired facts: 1

### Currently Valid Facts
1. "The pilot remains active."
2. "Capacity is scheduled to increase."

### Historical or Expired Facts
1. "The original delivery target expired."

### Core Entities
- **Orion Labs** (Company)
- **Delta Grid** (Utility)`

const interviewOutput = `## In-depth Interview Report
### Interview Topic
Storage partnership outlook
Interviewed 1 of 2 agents.

### Selection Rationale
1. **Maya Chen**: Covers the companies and their supply chain.

---

### Interview Transcript

#### interview #1: Maya Chen
**Maya Chen** (Analyst)
_Introduction: Energy markets analyst._

**Q:** What changed in the partnership?

**A:** [Twitter Platform answer]
The pilot announcement drew strong industry attention.

[Reddit Platform answer]
Operators focused on the accelerated capacity tests.

##### Key Quotes
> "Demand is accelerating."

---

### Interview Summary and Key Points
The partnership is more likely to expand than contract.`

const quickSearchOutput = `### Search Query
Orion Labs
Found 3 related items.

### Related Facts
1. Orion Labs reserved capacity.

### Related Edges
1. {"name":"SUPPLIES","source_node_name":"Orion Labs","target_node_name":"Delta Grid"}

### Related Nodes
1. {"name":"Orion Labs","labels":["Entity","Company"]}`

test('parseInsightForge consumes backend heading-plus-next-line output', () => {
  assert.deepEqual(parseInsightForge(insightForgeOutput), {
    query: 'Will Orion Labs expand its energy-storage partnership?',
    simulationRequirement: 'Forecast the partnership through the next two quarters.',
    stats: { facts: 2, entities: 2, relationships: 1 },
    subQueries: ['What capacity has been announced?', 'Which suppliers are exposed?'],
    facts: [
      'Orion Labs reserved additional battery capacity.',
      'Delta Grid approved a pilot expansion.'
    ],
    entities: [{
      name: 'Orion Labs',
      type: 'Company',
      summary: 'A storage technology company.',
      relatedFactsCount: 2
    }],
    relations: [{ source: 'Orion Labs', relation: 'SUPPLIES', target: 'Delta Grid' }]
  })
})

test('parsePanorama consumes backend statistics and section headings', () => {
  assert.deepEqual(parsePanorama(panoramaOutput), {
    query: 'Orion Labs storage partnership',
    stats: { nodes: 3, edges: 2, activeFacts: 2, historicalFacts: 1 },
    activeFacts: ['The pilot remains active.', 'Capacity is scheduled to increase.'],
    historicalFacts: ['The original delivery target expired.'],
    entities: [
      { name: 'Orion Labs', type: 'Company', summary: '', relatedFactsCount: 0 },
      { name: 'Delta Grid', type: 'Utility', summary: '', relatedFactsCount: 0 }
    ]
  })
})

test('parseInterview consumes backend topic, count, transcript, quotes, and summary', () => {
  const result = parseInterview(interviewOutput)

  assert.equal(result.topic, 'Storage partnership outlook')
  assert.equal(result.agentCount, '1 / 2')
  assert.equal(result.selectionReason, '1. **Maya Chen**: Covers the companies and their supply chain.')
  assert.equal(result.summary, 'The partnership is more likely to expand than contract.')
  assert.deepEqual(result.interviews, [{
    num: 1,
    title: 'Maya Chen',
    name: 'Maya Chen',
    role: 'Analyst',
    bio: 'Energy markets analyst.',
    selectionReason: 'Covers the companies and their supply chain.',
    questions: ['What changed in the partnership?'],
    twitterAnswer: 'The pilot announcement drew strong industry attention.',
    redditAnswer: 'Operators focused on the accelerated capacity tests.',
    quotes: ['Demand is accelerating.']
  }])
})

test('parseQuickSearch consumes backend query, count, and numbered JSON sections', () => {
  assert.deepEqual(parseQuickSearch(quickSearchOutput), {
    query: 'Orion Labs',
    count: 3,
    facts: ['Orion Labs reserved capacity.'],
    edges: [{ source: 'Orion Labs', relation: 'SUPPLIES', target: 'Delta Grid' }],
    nodes: [{ name: 'Orion Labs', type: 'Company' }]
  })
})
