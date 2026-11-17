import { ApiError } from '../lib/api'
import type { components } from '../lib/api-schema'
import type {
  FieldChange,
  IssueType,
  ProposedAction,
  Readiness,
  ReadinessRule,
  SpecSection,
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

export function fromApiAction(action: ApiAction): ProposedAction {
  const preview = action.preview
  return {
    id: action.id,
    kind: action.kind,
    projectKey: str(preview.project_key),
    projectName: str(preview.project_name) ?? '',
    issueKey: str(preview.issue_key),
    issueType: (str(preview.issue_type) as IssueType | null) ?? null,
    title: str(preview.summary) ?? '',
    priority: str(preview.priority),
    parentKey: str(preview.parent_key),
    labels: action.labels,
    sections: sections(preview),
    readiness: readiness(action.readiness),
    changes: changes(preview, action),
    expiresAt: action.expires_at,
    status: action.status,
    resultKey: action.result?.issue_key ?? null,
    resultUrl: action.result?.url ?? null,
    error: action.error?.message ?? null,
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
