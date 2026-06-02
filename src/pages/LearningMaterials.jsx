import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { Download, FileText, Loader2, Trash2, UploadCloud } from 'lucide-react'
import api from '../lib/api'
import { useAuth } from '../context/AuthContext'

function formatSize(bytes = 0) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatDate(value) {
  if (!value) return ''
  return new Date(value).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}

export default function LearningMaterials() {
  const { isAdmin } = useAuth()
  const [materials, setMaterials] = useState([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [title, setTitle] = useState('')
  const [file, setFile] = useState(null)

  const loadMaterials = async () => {
    setLoading(true)
    try {
      const { data } = await api.get('/api/materials')
      setMaterials(data)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Unable to load learning materials')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadMaterials()
  }, [])

  const handleUpload = async (event) => {
    event.preventDefault()
    if (!title.trim()) { toast.error('Enter a title'); return }
    if (!file) { toast.error('Select a PDF file'); return }

    const form = new FormData()
    form.append('title', title.trim())
    form.append('file', file)
    setUploading(true)
    try {
      await api.post('/api/admin/materials', form)
      toast.success('Learning material uploaded')
      setTitle('')
      setFile(null)
      event.currentTarget.reset()
      await loadMaterials()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  const openMaterial = async (material) => {
    try {
      const { data } = await api.get(`/api/materials/${material.id}/download`, { responseType: 'blob' })
      const blob = new Blob([data], { type: 'application/pdf' })
      const url = window.URL.createObjectURL(blob)
      window.open(url, '_blank', 'noopener,noreferrer')
      window.setTimeout(() => window.URL.revokeObjectURL(url), 60_000)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Unable to open PDF')
    }
  }

  const deleteMaterial = async (material) => {
    if (!window.confirm(`Remove "${material.title}"?`)) return
    try {
      await api.delete(`/api/admin/materials/${material.id}`)
      toast.success('Learning material removed')
      await loadMaterials()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Unable to remove material')
    }
  }

  return (
    <div className="page-section">
      <div className="page-header">
        <div>
          <h1>Learning Material</h1>
          <p>PDF learning resources shared for Rescue 1122 staff practice.</p>
        </div>
      </div>

      {isAdmin && (
        <form className="material-upload-panel" onSubmit={handleUpload}>
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label">Material Title</label>
            <input className="form-input" value={title} onChange={event => setTitle(event.target.value)} placeholder="Enter PDF title" maxLength={255} />
          </div>
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label">PDF File</label>
            <input className="form-input" type="file" accept="application/pdf,.pdf" onChange={event => setFile(event.target.files?.[0] || null)} />
          </div>
          <button className="btn btn-primary" type="submit" disabled={uploading}>
            {uploading ? <Loader2 size={16} className="spin" /> : <UploadCloud size={16} />}
            Upload PDF
          </button>
        </form>
      )}

      {loading ? (
        <div className="empty-state">Loading learning materials...</div>
      ) : materials.length === 0 ? (
        <div className="empty-state">No learning materials have been uploaded yet.</div>
      ) : (
        <div className="materials-grid">
          {materials.map(material => (
            <article className="material-card" key={material.id}>
              <div className="material-icon"><FileText size={22} /></div>
              <div className="material-body">
                <h2>{material.title}</h2>
                <p>{material.filename}</p>
                <div className="material-meta">
                  <span>{formatSize(material.file_size)}</span>
                  <span>{formatDate(material.created_at)}</span>
                  {material.uploaded_by_name && <span>By {material.uploaded_by_name}</span>}
                </div>
              </div>
              <div className="material-actions">
                <button className="btn btn-secondary btn-sm" onClick={() => openMaterial(material)}>
                  <Download size={15} /> Open
                </button>
                {isAdmin && (
                  <button className="btn btn-danger btn-sm" onClick={() => deleteMaterial(material)} title="Remove material">
                    <Trash2 size={15} />
                  </button>
                )}
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  )
}
