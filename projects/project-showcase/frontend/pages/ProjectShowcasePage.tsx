import { useEffect, useState } from 'react'
import { PageContainer } from '@shell/components/layout/PageContainer'
import { PageHeader } from '@shell/components/layout/PageHeader'
import { SectionHeader } from '@shell/components/layout/SectionHeader'
import projectManifest from '../../project.json'
import {
  getShowcaseInfo,
  showcaseRequestTimeoutMs,
  type ShowcaseInfo,
} from '../api'
import { ShowcaseCard } from '../components/ShowcaseCard'

type ConnectionState =
  | { status: 'loading' }
  | { status: 'ok'; info: ShowcaseInfo }
  | { status: 'error'; message: string }

function useShowcaseConnection(): ConnectionState {
  const [connection, setConnection] = useState<ConnectionState>({ status: 'loading' })

  useEffect(() => {
    const controller = new AbortController()
    const timeoutId = window.setTimeout(() => controller.abort(), showcaseRequestTimeoutMs())
    let active = true

    getShowcaseInfo(controller.signal)
      .then((info) => {
        if (active) {
          setConnection({ status: 'ok', info })
        }
      })
      .catch((error: unknown) => {
        if (!active) {
          return
        }
        if (error instanceof DOMException && error.name === 'AbortError') {
          setConnection({
            status: 'error',
            message: 'Request timed out after 5 seconds',
          })
          return
        }
        const message = error instanceof Error ? error.message : 'Unknown request error'
        setConnection({ status: 'error', message })
      })
      .finally(() => {
        window.clearTimeout(timeoutId)
      })

    return () => {
      active = false
      controller.abort()
    }
  }, [])

  return connection
}

export function ProjectShowcasePage() {
  const connection = useShowcaseConnection()
  const backendReady = connection.status === 'ok'

  return (
    <PageContainer>
      <PageHeader
        title="Project Showcase"
        description="A demonstration of the modular architecture."
      />

      <section className="showcase-section" aria-labelledby="showcase-information">
        <SectionHeader
          id="showcase-information"
          title="Project information"
          description="Values read from this module's project.json."
        />
        <dl className="showcase-definition-list">
          <div>
            <dt>Name</dt>
            <dd>{projectManifest.name}</dd>
          </div>
          <div>
            <dt>Description</dt>
            <dd>{projectManifest.description}</dd>
          </div>
          <div>
            <dt>Id</dt>
            <dd>{projectManifest.id}</dd>
          </div>
          <div>
            <dt>Schema version</dt>
            <dd>{projectManifest.schemaVersion}</dd>
          </div>
          <div>
            <dt>Route</dt>
            <dd>{projectManifest.routeBase}</dd>
          </div>
          <div>
            <dt>API prefix</dt>
            <dd>{projectManifest.apiPrefix}</dd>
          </div>
        </dl>
      </section>

      <section className="showcase-section" aria-labelledby="showcase-architecture">
        <SectionHeader
          id="showcase-architecture"
          title="Architecture overview"
          description="One shell, one API process, and independent project folders."
        />
        <div className="showcase-grid">
          <ShowcaseCard title="Shared Frontend Shell">
            <p>
              The shell owns the sidebar, header, layout, and router. It discovers
              project pages from each manifest.
            </p>
          </ShowcaseCard>
          <ShowcaseCard title="Shared Backend Core">
            <p>
              The FastAPI app owns CORS, the health endpoint, and project router
              registration.
            </p>
          </ShowcaseCard>
          <ShowcaseCard title="Independent Project Modules">
            <p>
              Each project keeps its own frontend, backend, and manifest. Modules
              do not import one another.
            </p>
          </ShowcaseCard>
        </div>
      </section>

      <section className="showcase-section" aria-labelledby="showcase-connectivity">
        <SectionHeader
          id="showcase-connectivity"
          title="Backend connectivity"
          description="Live response from this module's info endpoint."
        />
        {connection.status === 'loading' ? (
          <p className="showcase-state" role="status">
            Loading showcase API…
          </p>
        ) : null}
        {connection.status === 'error' ? (
          <p className="showcase-state showcase-state-error" role="alert">
            Showcase API unavailable. {connection.message}
          </p>
        ) : null}
        {connection.status === 'ok' ? (
          <div className="showcase-payload">
            <p className="showcase-state showcase-state-ok" role="status">
              Connected
            </p>
            <dl className="showcase-definition-list">
              <div>
                <dt>id</dt>
                <dd>{connection.info.id}</dd>
              </div>
              <div>
                <dt>name</dt>
                <dd>{connection.info.name}</dd>
              </div>
              <div>
                <dt>description</dt>
                <dd>{connection.info.description}</dd>
              </div>
              <div>
                <dt>status</dt>
                <dd>{connection.info.status}</dd>
              </div>
              <div>
                <dt>message</dt>
                <dd>{connection.info.message}</dd>
              </div>
            </dl>
          </div>
        ) : null}
      </section>

      <section className="showcase-section" aria-labelledby="showcase-integration">
        <SectionHeader
          id="showcase-integration"
          title="Module integration status"
          description="Frontend discovery is visible because this page rendered. Backend status comes from the API call."
        />
        <ul className="showcase-status-list">
          <li>
            <span className="showcase-state showcase-state-ok">Frontend route</span>
            <span>
              Opened at {projectManifest.routeBase} from the discovered manifest.
            </span>
          </li>
          <li>
            {backendReady ? (
              <span className="showcase-state showcase-state-ok">Backend module</span>
            ) : (
              <span className="showcase-state showcase-state-error">Backend module</span>
            )}
            <span>
              {connection.status === 'ok'
                ? connection.info.message
                : connection.status === 'error'
                  ? `The info request failed: ${connection.message}`
                  : 'Waiting for a successful info response before reporting the module as loaded.'}
            </span>
          </li>
        </ul>
      </section>
    </PageContainer>
  )
}
