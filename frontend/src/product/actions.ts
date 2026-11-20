import { ApiError } from '../lib/api'
import type { components } from '../lib/api-schema'
import {
  DOC_KINDS,
  type DocConflict,
  type DocProposal,
  type FieldChange,
  type IssueType,
  type PageDiff,
  type ProposedAction,
  type Readiness,
  type ReadinessRule,
  type SpecSection,
} from './types'

export type ApiAction = components['schemas']['ActionOut']

type Preview = Record<string, unknown>

const str = (value: unknown): string | null => (typeof value === 'string' ? value : null)
const strings = (value: unknown): string[] =>
  Array.isArray(value) ? value.filter((v): v is string => typeof v === 'string') : []

function sections(preview: Preview): SpecSection[] {
  const raw = Array.isArray(preview.sections) ? (preview.sections as unknown[]) : []
  return raw.flatMap((s) => {
    const section = s as Preview
    const title = str(section.title)
    return title ? [{ title, markdown: str(section.markdown) ?? '' }] : []
  })
}

function readiness(raw: Preview): Readiness | null {
  if (typeof raw.ready !== 'boolean') return null
  const rules = (Array.isArray(raw.rules) ? (raw.rules as Preview[]) : []).map(
    (r): ReadinessRule => ({
      id: str(r.id) ?? '',
      label: str(r.label) ?? '',
      severity: str(r.severity) ?? '',
      passed: r.passed === true,
      detail: str(r.detail) ?? '',
    }),
  )
  return { ready: raw.ready, rules }
}

function conflicts(preview: Preview): DocConflict[] {
  const raw = Array.isArray(preview.conflicts) ? (preview.conflicts as Preview[]) : []
  return raw.flatMap((c) => {
    const id = str(c.id)
    return id ? [{ id, reason: str(c.reason) ?? '' }] : []
  })
}

/** Antes/depois só dos campos que a atualização muda (F06-RF-06). */
function changes(preview: Preview, action: ApiAction): FieldChange[] {
  const before = (preview.before ?? null) as Preview | null
  if (action.kind !== 'update_issue' || !before) return []
  const out: FieldChange[] = []
  if ('summary' in before)
    out.push({
      field: 'summary',
      before: str(before.summary) ?? '',
      after: str(preview.summary) ?? '',
    })
  if ('markdown' in before)
    out.push({
      field: 'description',
      before: str(before.markdown) ?? '',
      after: str(preview.markdown) ?? '',
    })
  if ('priority' in before)
    out.push({
      field: 'priority',
      before: str(before.priority) ?? '—',
      after: str(preview.priority) ?? '',
    })
  if ('labels' in before)
    out.push({
      field: 'labels',
      before: strings(before.labels).join(', ') || '—',
      after: action.labels.join(', ') || '—',
    })
  return out
}

function diff(preview: Preview): PageDiff[] {
  const raw = Array.isArray(preview.diff) ? (preview.diff as Preview[]) : []
  return raw.flatMap((d) => {
    const change = str(d.change)
    if (change !== 'added' && change !== 'removed' && change !== 'changed') return []
    return [
      {
        section: str(d.section) ?? '',
        change,
        before: str(d.before) ?? '',
        after: str(d.after) ?? '',
      },
    ]
  })
}

function doc(action: ApiAction): DocProposal | null {
  if (!DOC_KINDS.includes(action.kind)) return null
  const preview = action.preview
  const space = (preview.space ?? null) as Preview | null
  return {
    pageType: str(preview.page_type) ?? '',
    summary: str(preview.summary) ?? '',
    space:
      space && str(space.key)
        ? { key: str(space.key) ?? '', name: str(space.name) ?? '', url: str(space.url) ?? '' }
        : null,
    parentTitle: str(preview.parent_title),
    url: str(preview.url),
    version: typeof preview.version === 'number' ? preview.version : null,
    previousTitle: str(preview.previous_title),
    diff: diff(preview),
    spaceKey: str(preview.space_key),
    pages: strings(preview.pages),
  }
}

export function fromApiAction(action: ApiAction): ProposedAction {
  const preview = action.preview
  const result = action.result ?? null
  const docs = doc(action)
  return {
    id: action.id,
    kind: action.kind,
    projectKey: str(preview.project_key),
    projectName: str(preview.project_name) ?? '',
    issueKey: str(preview.issue_key),
    issueType: (str(preview.issue_type) as IssueType | null) ?? null,
    title: (docs ? str(preview.title) : str(preview.summary)) ?? '',
    priority: str(preview.priority),
    parentKey: str(preview.parent_key),
    labels: action.labels,
    sections: sections(preview),
    readiness: readiness(action.readiness),
    conflicts: conflicts(preview),
    changes: changes(preview, action),
    expiresAt: action.expires_at,
    status: action.status,
    resultKey: result && 'issue_key' in result ? result.issue_key : null,
    resultUrl: result?.url ?? null,
    error: action.error?.message ?? null,
    errorCode: action.error?.code ?? null,
    doc: docs,
    warning: result && 'warning' in result ? (result.warning ?? null) : null,
  }
}

/**
 * Erro da confirmação que traz o estado atual da ação (409 já tratada, 410 expirada, 422 erro do
 * Jira): o cartão mostra o novo estado em vez de um erro genérico.
 */
export class ActionProblem extends Error {
  constructor(
    readonly code: string,
    message: string,
    readonly action: ProposedAction,
  ) {
    super(message)
    this.name = 'ActionProblem'
  }
}

export function toActionProblem(error: unknown): unknown {
  if (error instanceof ApiError && error.body.action && typeof error.body.action === 'object') {
    return new ActionProblem(
      error.code,
      error.message,
      fromApiAction(error.body.action as ApiAction),
    )
  }
  return error
}

/** Cartão a partir do evento `action_proposed` do streaming (antes de o histórico ser relido). */
export function fromProposedEvent(
  event: { action_id: string; kind: ApiAction['kind']; preview: Record<string, unknown> },
  conversationId: string,
  now: Date = new Date(),
): ProposedAction {
  const preview = event.preview
  const readinessRaw = (preview.readiness ?? {}) as ApiAction['readiness']
  return fromApiAction({
    id: event.action_id,
    kind: event.kind,
    status: 'pending',
    conversation_id: conversationId,
    preview,
    readiness: readinessRaw,
    labels: strings(preview.labels),
    created_at: now.toISOString(),
    expires_at: new Date(now.getTime() + 24 * 3_600_000).toISOString(),
  })
}
