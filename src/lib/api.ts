// Netzwerkzugriffe mit Zeitlimit; alle URLs relativ, damit der Subpath (/favicon-tool/) passt.

export class HttpError extends Error {}

/** fetch mit Abbruch nach `timeoutMs`; ein Abbruch wirft einen AbortError (DOMException). */
export async function fetchWithTimeout(
  url: string,
  init: RequestInit,
  timeoutMs: number
): Promise<Response> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  try {
    return await fetch(url, { ...init, signal: controller.signal })
  } finally {
    clearTimeout(timer)
  }
}

export function isAbortError(err: unknown): boolean {
  return err instanceof DOMException
    ? err.name === 'AbortError'
    : (err as { name?: string } | null)?.name === 'AbortError'
}

/** Fehlertext aus einer FastAPI-Antwort ({"detail": "..."}), sonst `fallback`. */
export async function errorDetail(res: Response, fallback: string): Promise<string> {
  try {
    const data: unknown = await res.json()
    if (data && typeof data === 'object' && 'detail' in data) {
      const detail = (data as { detail: unknown }).detail
      if (typeof detail === 'string') return detail
    }
  } catch {
    // keine JSON-Antwort
  }
  return fallback
}

/** Dateiname aus dem Content-Disposition-Header (attachment; filename=...), sonst `fallback`. */
export function dispositionFilename(res: Response, fallback: string): string {
  const header = res.headers.get('Content-Disposition') ?? ''
  const match = /filename="?([^";]+)"?/i.exec(header)
  const name = match?.[1]?.trim()
  // nur einfache Dateinamen übernehmen, keine Pfade
  return name && /^[\w.-]+$/.test(name) ? name : fallback
}

/** Blob als Datei herunterladen. */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
