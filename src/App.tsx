import { useEffect, useMemo, useState } from 'react'
import './App.css'

const API_BASE = 'http://localhost:8000'

function App() {
  const [githubUrl, setGithubUrl] = useState('https://github.com/tiangolo/fastapi')
  const [health, setHealth] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [taskId, setTaskId] = useState('')
  const [taskStatus, setTaskStatus] = useState<'idle' | 'running' | 'completed' | 'failed'>('idle')
  const [result, setResult] = useState<any>(null)

  useEffect(() => {
    fetchHealth()
  }, [])

  const fetchHealth = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/health`)
      const payload = await response.json()
      setHealth(payload)
    } catch {
      setHealth({ status: 'offline', note: '后端未启动' })
    }
  }

  const pollTask = async (newTaskId: string) => {
    const response = await fetch(`${API_BASE}/api/tasks/${newTaskId}`)
    if (!response.ok) {
      throw new Error('无法读取任务状态')
    }
    const payload = await response.json()

    if (payload.status === 'completed' || payload.status === 'failed') {
      setTaskStatus(payload.status)
      setResult(payload.data ?? payload)
      setLoading(false)
      return
    }

    setTaskStatus('running')
    setTimeout(() => pollTask(newTaskId).catch(() => setLoading(false)), 1500)
  }

  const handleSubmit = async () => {
    if (!githubUrl.trim()) {
      setError('请输入 GitHub 仓库 URL')
      return
    }

    setLoading(true)
    setError('')
    setTaskStatus('running')
    setResult(null)

    try {
      const response = await fetch(`${API_BASE}/api/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ github_url: githubUrl }),
      })

      const payload = await response.json()
      if (!response.ok) {
        throw new Error(payload.detail ?? '分析请求失败')
      }

      const nextTaskId = payload.task_id
      setTaskId(nextTaskId)
      await pollTask(nextTaskId)
    } catch (submitError: any) {
      setError(submitError.message || '请求失败')
      setTaskStatus('failed')
      setLoading(false)
    }
  }

  const onDownload = () => {
    if (!result?.document) {
      return
    }

    const blob = new Blob([result.document], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `${(result.repo?.full_name || 'repodoc').split('/').pop() || 'repodoc'}.md`
    anchor.click()
    URL.revokeObjectURL(url)
  }

  const repoName = useMemo(() => result?.repo?.full_name || '尚未分析', [result])
  const semanticEntries = useMemo(() => Object.entries(result?.semantic_layer?.by_type || {}), [result])
  const semanticCards = [
    {
      title: '职责 1',
      body: 'README、源码、依赖、API 路由被统一映射成实体与关系，避免信息碎片化。',
    },
    {
      title: '职责 2',
      body: '语义层对模块、类、函数、API、依赖做标准化命名，方便 Agent 检索与生成文档。',
    },
    {
      title: '职责 3',
      body: '它把检索结果和图谱结果串起来，确保文档生成基于真实仓库事实，而不是模板内容。',
    },
  ]

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">RepoDoc Agent</p>
          <h1>GitHub → 온톨로지 → 지식 그래프 → 문서 생성</h1>
        </div>
        <div className="badge-group">
          <span className={`status-pill ${health?.status === 'ok' ? 'ok' : 'warn'}`}>
            {health?.status === 'ok' ? '백엔드 정상' : '백엔드 오프라인'}
          </span>
          <span className="status-pill neutral">{health?.gemini_configured ? 'Gemini 준비됨' : 'API 키 필요'}</span>
        </div>
      </header>

      <main className="dashboard">
        <section className="panel form-panel">
          <label htmlFor="githubUrl" className="label">GitHub URL</label>
          <div className="input-row">
            <input
              id="githubUrl"
              value={githubUrl}
              onChange={(event) => setGithubUrl(event.target.value)}
              placeholder="https://github.com/owner/repo"
            />
            <button type="button" onClick={handleSubmit} disabled={loading}>
              {loading ? '분석 중...' : '분석 시작'}
            </button>
          </div>
          <p className="helper-text">
            실제 GitHub 저장소 URL을 입력하면 소스코드를 자동 수집하고 지식 그래프를 추출해 기술 문서를 생성합니다.
          </p>
          {error && <div className="error-box">{error}</div>}
          {taskId && <div className="task-box">작업 ID: {taskId}</div>}
        </section>

        <section className="panel metrics-panel">
          <div className="metric-card">
            <span>상태</span>
            <strong>{taskStatus}</strong>
          </div>
          <div className="metric-card">
            <span>모듈 수</span>
            <strong>{result?.modules?.length || 0}</strong>
          </div>
          <div className="metric-card">
            <span>API</span>
            <strong>{result?.api_endpoints?.length || 0}</strong>
          </div>
          <div className="metric-card">
            <span>의존성</span>
            <strong>{result?.dependencies?.length || 0}</strong>
          </div>
        </section>

        {!result && !loading && (
          <section className="panel empty-panel">
            아직 결과가 없습니다. 저장소 주소를 입력하면 전체 분석 흐름이 시작됩니다.
          </section>
        )}

        {result && (
          <>
            <section className="panel overview-panel">
              <div className="section-heading">
                <h2>저장소 개요</h2>
                <button type="button" className="secondary" onClick={onDownload}>
                  Markdown 내보내기
                </button>
              </div>

              <div className="overview-grid">
                <div>
                  <label>프로젝트</label>
                  <p>{repoName}</p>
                </div>
                <div>
                  <label>언어</label>
                  <p>{result.tech_stack?.join(', ') || '알 수 없음'}</p>
                </div>
                <div>
                  <label>브랜치</label>
                  <p>{result.repo?.default_branch || 'main'}</p>
                </div>
                <div>
                  <label>설명</label>
                  <p>{result.repo?.description || '설명 없음'}</p>
                </div>
              </div>
            </section>

            <section className="panel two-column">
              <div>
                <h3>클래스</h3>
                <ul className="list-box">
                  {(result.classes || []).slice(0, 10).map((item: any, index: number) => (
                    <li key={`${item.name}-${index}`}>
                      {item.name} · {item.path || item.module || 'n/a'}
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <h3>함수</h3>
                <ul className="list-box">
                  {(result.functions || []).slice(0, 10).map((item: any, index: number) => (
                    <li key={`${item.name}-${index}`}>
                      {item.name} · {item.path || item.module || 'n/a'}
                    </li>
                  ))}
                </ul>
              </div>
            </section>

            <section className="panel two-column">
              <div>
                <h3>API 엔드포인트</h3>
                <ul className="list-box">
                  {(result.api_endpoints || []).slice(0, 10).map((item: any, index: number) => (
                    <li key={`${item.method}-${item.path}-${index}`}>
                      {item.method} {item.path} → {item.handler}
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <h3>의존성</h3>
                <ul className="list-box">
                  {(result.dependencies || []).slice(0, 10).map((item: any, index: number) => (
                    <li key={`${item.name}-${index}`}>
                      {item.name} {item.version ? `(${item.version})` : ''}
                    </li>
                  ))}
                </ul>
              </div>
            </section>

            <section className="panel graph-panel" style={{ padding: '24px' }}>
              <div className="section-heading" style={{ marginBottom: '18px' }}>
                <h2>Semantic Layer 역할</h2>
              </div>

              <div style={{ display: 'grid', gap: '16px' }}>
                <div style={{ background: '#101827', border: '1px solid #2b3a52', borderRadius: '12px', padding: '18px' }}>
                  <div style={{ fontSize: '12px', letterSpacing: '0.08em', textTransform: 'uppercase', color: '#8ab4f8', marginBottom: '8px' }}>
                    Semantic Layer
                  </div>
                  <h3 style={{ margin: '0 0 10px', color: '#edf6ff' }}>이 레이어는 “저장소를 이해하는 중간층”입니다.</h3>
                  <p style={{ margin: 0, lineHeight: 1.7, color: '#dfeaf7' }}>
                    README, 소스코드, 라우트, 클래스, 함수, 의존성 정보를 하나의 의미 체계로 통합해
                    지식 그래프와 RAG 가 바로 사용할 수 있는 표준 구조로 변환합니다.
                  </p>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '12px' }}>
                  {semanticCards.map((card) => (
                    <div key={card.title} style={{ background: '#0f172a', border: '1px solid #334155', borderRadius: '10px', padding: '16px' }}>
                      <div style={{ fontWeight: 700, color: '#7dd3fc', marginBottom: '8px' }}>{card.title}</div>
                      <div style={{ color: '#dbeafe', lineHeight: 1.7 }}>{card.body}</div>
                    </div>
                  ))}
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px' }}>
                  <div style={{ background: '#0b1220', border: '1px solid #233248', borderRadius: '10px', padding: '14px' }}>
                    <div style={{ color: '#9fb4d4', fontSize: '12px' }}>Entity count</div>
                    <div style={{ fontSize: '28px', fontWeight: 700, color: '#e2e8f0' }}>{result.semantic_layer?.entity_count || 0}</div>
                  </div>
                  <div style={{ background: '#0b1220', border: '1px solid #233248', borderRadius: '10px', padding: '14px' }}>
                    <div style={{ color: '#9fb4d4', fontSize: '12px' }}>Relationship count</div>
                    <div style={{ fontSize: '28px', fontWeight: 700, color: '#e2e8f0' }}>{result.semantic_layer?.relationship_count || 0}</div>
                  </div>
                  <div style={{ background: '#0b1220', border: '1px solid #233248', borderRadius: '10px', padding: '14px' }}>
                    <div style={{ color: '#9fb4d4', fontSize: '12px' }}>Graph status</div>
                    <div style={{ fontSize: '28px', fontWeight: 700, color: '#e2e8f0' }}>{result.knowledge_graph?.status || 'unknown'}</div>
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1.3fr 1fr', gap: '12px' }}>
                  <div style={{ background: '#0f172a', border: '1px solid #334155', borderRadius: '10px', padding: '16px' }}>
                    <h4 style={{ marginTop: 0, color: '#f8fafc' }}>Semantic Mapping</h4>
                    <ul style={{ margin: 0, paddingLeft: '18px', color: '#dbeafe', lineHeight: 1.9 }}>
                      {semanticEntries.length > 0 ? semanticEntries.map(([key, value]) => (
                        <li key={key}><strong>{key}</strong>: {value}</li>
                      )) : <li>현재 확인된 의미 엔티티가 없습니다.</li>}
                    </ul>
                  </div>
                  <div style={{ background: '#0f172a', border: '1px solid #334155', borderRadius: '10px', padding: '16px' }}>
                    <h4 style={{ marginTop: 0, color: '#f8fafc' }}>Agent Query Flow</h4>
                    <ol style={{ margin: 0, paddingLeft: '18px', color: '#dbeafe', lineHeight: 1.9 }}>
                      <li>Repository facts</li>
                      <li>Ontology entities</li>
                      <li>Semantic layer</li>
                      <li>Knowledge graph</li>
                      <li>RAG retrieval</li>
                      <li>Document generation</li>
                    </ol>
                  </div>
                </div>
              </div>
            </section>

            <section className="panel two-column">
              <div>
                <h3>RAG 증거</h3>
                <pre>{JSON.stringify(result.rag_evidence || result.rag || [], null, 2)}</pre>
              </div>
              <div>
                <h3>Gemini 및 Agent 상태</h3>
                <pre>{JSON.stringify({ gemini: result.gemini_status || { configured: false, status: 'missing_gemini_api_key' }, agent: result.agent_status || { status: 'unknown' } }, null, 2)}</pre>
              </div>
            </section>

            <section className="panel doc-panel">
              <div className="section-heading">
                <h2>생성된 기술 문서</h2>
              </div>
              {!health?.gemini_configured && (
                <div className="error-box">
                  현재 GEMINI_API_KEY가 감지되지 않아 문서는 저장소 사실 기반의 규칙 출력으로 대체되며, 결과에 “저장소에서 관련 정보를 찾을 수 없음”이 명시됩니다.
                </div>
              )}
              <pre className="markdown-box">{result.document || '아직 문서가 생성되지 않았습니다.'}</pre>
            </section>
          </>
        )}
      </main>
    </div>
  )
}

export default App
