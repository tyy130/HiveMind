function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function normalizeText(text) {
  return String(text || '').replace(/\r\n?/g, '\n')
}

function extractMarkdownSection(text, heading) {
  const normalized = normalizeText(text)
  const escapedHeading = escapeRegExp(heading)
  const pattern = new RegExp(
    `^#{1,6}[ \\t]+${escapedHeading}[ \\t]*:?[ \\t]*\\n([\\s\\S]*?)(?=^#{1,6}[ \\t]+|(?![\\s\\S]))`,
    'im'
  )
  const section = normalized.match(pattern)?.[1]?.trim() || ''
  return section.replace(/\n*[ \t]*---[ \t]*$/, '').trim()
}

function extractSection(text, headings) {
  for (const heading of headings) {
    const section = extractMarkdownSection(text, heading)
    if (section) return section
  }
  return ''
}

function extractHeadingValue(text, headings, inlineLabels = headings) {
  const section = extractSection(text, headings)
  if (section) {
    return section.split('\n').map(line => line.trim()).find(Boolean) || ''
  }

  const normalized = normalizeText(text)
  for (const label of inlineLabels) {
    const escapedLabel = escapeRegExp(label)
    const pattern = new RegExp(`^(?:\\*\\*)?${escapedLabel}:?(?:\\*\\*)?[ \\t]+(.+)$`, 'im')
    const value = normalized.match(pattern)?.[1]?.trim()
    if (value) return value
  }
  return ''
}

function extractCount(text, labels) {
  const normalized = normalizeText(text)
  for (const label of labels) {
    const escapedLabel = escapeRegExp(label)
    const pattern = new RegExp(`^[ \\t]*(?:-[ \\t]*)?(?:\\*\\*)?${escapedLabel}:(?:\\*\\*)?[ \\t]*(\\d+)`, 'im')
    const value = normalized.match(pattern)?.[1]
    if (value) return Number.parseInt(value, 10)
  }
  return 0
}

function parseNumberedItems(section) {
  return section
    .split('\n')
    .map(line => line.match(/^\s*\d+\.\s*(.+)$/)?.[1]?.trim())
    .filter(Boolean)
    .map(value => value.replace(/^"|"$/g, '').trim())
}

function parseStructuredItems(section) {
  return section
    .split('\n')
    .map(line => line.match(/^\s*(?:\d+\.|-)\s*(.+)$/)?.[1]?.trim())
    .filter(Boolean)
}

function parseEntities(section) {
  const entityBlocks = section.split(/\n(?=-\s*\*\*)/).filter(block => block.trim().startsWith('- **'))
  return entityBlocks.map(block => {
    const nameMatch = block.match(/^-\s*\*\*(.+?)\*\*\s*\((.+?)\)/)
    const summaryMatch = block.match(/^\s*Summary:\s*"?(.+?)"?\s*$/im)
    const relatedMatch = block.match(/^\s*Relevant facts:\s*(\d+)\s*$/im)
    return {
      name: nameMatch?.[1]?.trim() || '',
      type: nameMatch?.[2]?.trim() || '',
      summary: summaryMatch?.[1]?.replace(/"$/, '').trim() || '',
      relatedFactsCount: relatedMatch ? Number.parseInt(relatedMatch[1], 10) : 0
    }
  }).filter(entity => entity.name)
}

function parseRelationshipChains(section) {
  return section.split('\n').map(line => {
    const match = line.match(/^-\s*(.+?)\s*--\[(.+?)\]-->\s*(.+)$/)
    if (!match) return null
    return { source: match[1].trim(), relation: match[2].trim(), target: match[3].trim() }
  }).filter(Boolean)
}

function parseJsonList(section) {
  return parseStructuredItems(section).map(value => {
    try {
      return JSON.parse(value)
    } catch {
      return value
    }
  })
}

export function parseInsightForge(text) {
  const result = {
    query: extractHeadingValue(text, ['Analysis Question']),
    simulationRequirement: extractHeadingValue(text, ['Prediction Scenario']),
    stats: {
      facts: extractCount(text, ['Relevant prediction facts', 'Relevant predictive facts']),
      entities: extractCount(text, ['Involved entities', 'Entities involved']),
      relationships: extractCount(text, ['Relationship chains'])
    },
    subQueries: parseNumberedItems(extractSection(text, ['Analysis Questions', 'Analyzed Sub-questions'])),
    facts: parseNumberedItems(extractSection(text, ['Key Facts'])),
    entities: parseEntities(extractSection(text, ['Core Entities'])),
    relations: parseRelationshipChains(extractSection(text, ['Relationship Chains']))
  }

  return result
}

export function parsePanorama(text) {
  return {
    query: extractHeadingValue(text, ['Search Query'], ['Query', 'Search Query']),
    stats: {
      nodes: extractCount(text, ['Total number of nodes', 'Total nodes']),
      edges: extractCount(text, ['Total number of edges', 'Total edges']),
      activeFacts: extractCount(text, ['Currently valid facts']),
      historicalFacts: extractCount(text, ['Historical or expired facts', 'Historical/expired facts'])
    },
    activeFacts: parseNumberedItems(extractSection(text, ['Currently Valid Facts'])),
    historicalFacts: parseNumberedItems(extractSection(text, ['Historical or Expired Facts', 'Historical/Expired Facts'])),
    entities: parseEntities(extractSection(text, ['Core Entities', 'Relevant Entities']))
  }
}

function parseIndividualReasons(reasonText) {
  const reasons = {}
  const lines = reasonText.split(/\n+/)
  let currentName = null
  let currentReason = []

  const saveCurrentReason = () => {
    if (currentName && currentReason.length > 0) {
      reasons[currentName] = currentReason.join(' ').trim()
    }
  }

  for (const line of lines) {
    const patterns = [
      /^\d+\.\s*\*\*([^*(]+)(?:\(index\s*=?\s*\d+\))?\*\*:\s*(.*)/i,
      /^-\s*Selected\s+([^\(]+)(?:\(index\s*=?\s*\d+\))?:\s*(.*)/i,
      /^-\s*\*\*([^*(]+)(?:\(index\s*=?\s*\d+\))?\*\*:\s*(.*)/i
    ]
    const match = patterns.map(pattern => line.match(pattern)).find(Boolean)

    if (match) {
      saveCurrentReason()
      currentName = match[1].trim()
      currentReason = match[2] ? [match[2].trim()] : []
    } else if (currentName && line.trim() && !line.match(/^Not selected|^In summary|^Final selection/i)) {
      currentReason.push(line.trim())
    }
  }

  saveCurrentReason()
  return reasons
}

function parseQuotes(block) {
  const section = extractSection(block, ['Key Quotes'])
    || normalizeText(block).match(/(?:^|\n)\*\*Key Quotes:\*\*\s*\n([\s\S]*?)(?=\n---|\n####|(?![\s\S]))/i)?.[1]?.trim()
    || ''
  return section.split('\n').map(line => {
    const match = line.match(/^>\s*["“”]?(.+?)["“”]?\s*$/)
    return match?.[1]?.replace(/["“”]$/, '').trim()
  }).filter(Boolean)
}

export function parseInterview(text) {
  const result = {
    topic: extractHeadingValue(text, ['Interview Topic']),
    agentCount: '',
    successCount: 0,
    totalCount: 0,
    selectionReason: extractSection(text, ['Selection Rationale']),
    interviews: [],
    summary: extractSection(text, ['Interview Summary and Key Points', 'Interview Summary and Key Findings'])
  }

  const normalized = normalizeText(text)
  const countMatch = normalized.match(/Interviewed\s+(\d+)\s+of\s+(\d+)\s+agents?\./i)
    || normalized.match(/^(?:\*\*)?Interviewees:(?:\*\*)?\s*(\d+)\s*\/\s*(\d+)/im)
  if (countMatch) {
    result.successCount = Number.parseInt(countMatch[1], 10)
    result.totalCount = Number.parseInt(countMatch[2], 10)
    result.agentCount = `${countMatch[1]} / ${countMatch[2]}`
  }

  const individualReasons = parseIndividualReasons(result.selectionReason)
  const interviewBlocks = normalized.split(/^####\s+Interview\s+#\d+:\s*/gim).slice(1)

  interviewBlocks.forEach((block, index) => {
    const title = block.match(/^(.+?)\n/)?.[1]?.trim() || ''
    const nameRoleMatch = block.match(/\*\*(.+?)\*\*\s*\((.+?)\)/)
    const bioMatch = block.match(/_(?:Introduction|Bio):\s*([\s\S]*?)_\s*\n/i)
    const questionMatch = block.match(/\*\*Q:\*\*\s*([\s\S]*?)(?=\n\n\*\*A:\*\*|\*\*A:\*\*)/i)
    const questionText = questionMatch?.[1]?.trim() || ''
    const questionLines = questionText.split('\n').map(line => line.trim()).filter(Boolean)
    const numberedQuestions = questionLines.map(line => line.match(/^\d+\.\s*(.+)$/)?.[1]?.trim()).filter(Boolean)
    const answerMatch = block.match(/\*\*A:\*\*\s*([\s\S]*?)(?=\n#{1,6}\s+Key Quotes|\n\*\*Key Quotes:\*\*|\n---|(?![\s\S]))/i)
    const answerText = answerMatch?.[1]?.trim() || ''
    const twitterMatch = answerText.match(/\[Twitter (?:Response|Platform answer)\]\n?([\s\S]*?)(?=\[Reddit (?:Response|Platform answer)\]|$)/i)
    const redditMatch = answerText.match(/\[Reddit (?:Response|Platform answer)\]\n?([\s\S]*?)$/i)
    let twitterAnswer = twitterMatch?.[1]?.trim() || ''
    let redditAnswer = redditMatch?.[1]?.trim() || ''
    if (!twitterMatch && redditAnswer && redditAnswer !== '(No response from this platform)') {
      twitterAnswer = redditAnswer
    } else if (!redditMatch && twitterAnswer && twitterAnswer !== '(No response from this platform)') {
      redditAnswer = twitterAnswer
    } else if (!twitterMatch && !redditMatch) {
      twitterAnswer = answerText
    }
    const interview = {
      num: index + 1,
      title,
      name: nameRoleMatch?.[1]?.trim() || '',
      role: nameRoleMatch?.[2]?.trim() || '',
      bio: bioMatch?.[1]?.trim().replace(/\.\.\.$/, '...') || '',
      selectionReason: '',
      questions: numberedQuestions.length > 0 ? numberedQuestions : (questionText ? [questionText] : []),
      twitterAnswer,
      redditAnswer,
      quotes: parseQuotes(block)
    }
    interview.selectionReason = individualReasons[interview.name] || ''

    if (interview.name || interview.title) result.interviews.push(interview)
  })

  return result
}

export function parseQuickSearch(text) {
  const countMatch = normalizeText(text).match(/Found\s+(\d+)\s+(?:related items|results?)[\s.]/i)
  const edgeItems = parseJsonList(extractSection(text, ['Related Edges']))
  const nodeItems = parseJsonList(extractSection(text, ['Related Nodes']))

  return {
    query: extractHeadingValue(text, ['Search Query']),
    count: countMatch ? Number.parseInt(countMatch[1], 10) : 0,
    facts: parseNumberedItems(extractSection(text, ['Related Facts'])),
    edges: edgeItems.map(edge => {
      if (typeof edge === 'string') {
        const match = edge.match(/^(.+?)\s*--\[(.+?)\]-->\s*(.+)$/)
        return match ? { source: match[1], relation: match[2], target: match[3] } : null
      }
      return {
        source: edge.source_node_name || edge.source || edge.source_node_uuid || '',
        relation: edge.name || edge.relation || edge.fact || '',
        target: edge.target_node_name || edge.target || edge.target_node_uuid || ''
      }
    }).filter(edge => edge?.source || edge?.relation || edge?.target),
    nodes: nodeItems.map(node => {
      if (typeof node === 'string') {
        const match = node.match(/^\*\*(.+?)\*\*\s*\((.+?)\)$/)
        return match ? { name: match[1].trim(), type: match[2].trim() } : { name: node, type: '' }
      }
      const labels = Array.isArray(node.labels) ? node.labels : []
      const type = labels.find(label => !['Entity', 'Node'].includes(label)) || node.type || ''
      return { name: node.name || node.uuid || '', type }
    }).filter(node => node.name)
  }
}
