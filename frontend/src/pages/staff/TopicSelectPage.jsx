import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { getDesignationLabel, getTopicSectionsForDesignation } from '../../lib/topics'
import { ArrowLeft, BookOpen, ChevronRight, FileText } from 'lucide-react'

export default function TopicSelectPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const profile = user?.profile
  const designation = profile?.designation || 'rescue_officer'
  const designationLabel = getDesignationLabel(designation)
  const sections = getTopicSectionsForDesignation(designation)
  const [activeSection, setActiveSection] = useState(null)
  const [selected, setSelected] = useState(null)

  const selectedSection = sections.find(section => section.id === activeSection)

  const handleStart = () => {
    if (!selected) return
    navigate('/staff/exam', { state: { topic: selected, designation } })
  }

  const handleSectionSelect = (section) => {
    setSelected(null)
    setActiveSection(section.id)
  }

  const handleBackToSections = () => {
    setSelected(null)
    setActiveSection(null)
  }

  return (
    <div className="page-content fade-in">
      <div style={{ marginBottom: '1.5rem' }}>
        <h2>{selectedSection ? selectedSection.label : 'Take Examination'}</h2>
        <p style={{ marginTop: 4, color: 'var(--gray-500)' }}>
          Topics available for your designation: <strong>{designationLabel}</strong>. Each practice exam has 25 MCQs and a 30 minute countdown.
        </p>
      </div>

      <div className="alert alert-info" style={{ marginBottom: '1.25rem' }}>
        <FileText size={18} />
        <span>Read the official source material first, then select the correct section and topic according to your preparation before taking the test.</span>
      </div>

      {!selectedSection ? (
        <div className="exam-section-grid">
          {sections.map(section => (
            <button key={section.id} className={`exam-section-card exam-section-${section.id}`} onClick={() => handleSectionSelect(section)}>
              <span className="exam-section-icon">{section.icon}</span>
              <span className="exam-section-content">
                <span className="exam-section-title">{section.label}</span>
                <span className="exam-section-desc">{section.description}</span>
                <span className="exam-section-meta">{section.topics.length} topics available</span>
              </span>
              <ChevronRight size={22} />
            </button>
          ))}
        </div>
      ) : (
        <>
          <div className="section-row" style={{ marginBottom: '1rem' }}>
            <button className="btn btn-secondary" onClick={handleBackToSections}>
              <ArrowLeft size={16} /> Sections
            </button>
            <span className="badge badge-blue">{selectedSection.topics.length} topics</span>
          </div>

          <section className="card" style={{ padding: '1.25rem', marginBottom: '1.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem', marginBottom: '1rem' }}>
              <div className="mini-avatar" style={{ width: 44, height: 44, flexBasis: 44, fontSize: '1.35rem' }}>{selectedSection.icon}</div>
              <div>
                <h3 style={{ color: 'var(--blue-800)' }}>{selectedSection.label} Topics</h3>
                <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--gray-500)' }}>{selectedSection.description}</p>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: '0.85rem' }}>
              {selectedSection.topics.map(topic => {
                const isSelected = selected?.id === topic.id
                return (
                  <div
                    key={topic.id}
                    className="card card-hover"
                    style={{
                      cursor: 'pointer',
                      border: isSelected ? '2px solid var(--blue-500)' : '1px solid var(--line-blue)',
                      background: isSelected ? 'linear-gradient(135deg, var(--blue-50), var(--green-50))' : 'linear-gradient(180deg, #fff, var(--surface-blue))',
                      transition: 'all 0.18s',
                      padding: '1rem',
                    }}
                    onClick={() => setSelected(topic)}
                  >
                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.85rem' }}>
                      <div style={{ fontSize: 28, lineHeight: 1, flexShrink: 0 }}>{topic.icon}</div>
                      <div style={{ flex: 1 }}>
                        <h4 style={{ color: isSelected ? 'var(--blue-800)' : 'var(--gray-900)', marginBottom: 4 }}>{topic.label}</h4>
                        <p style={{ fontSize: '0.8rem', color: 'var(--gray-300)', margin: 0 }}>Source: {topic.source}</p>
                        <p style={{ fontSize: '0.8rem', color: 'var(--gray-400)', margin: '4px 0 0' }}>25 questions · 30 minutes · Pass at 60%</p>
                      </div>
                      {isSelected && (
                        <div style={{ width: 20, height: 20, borderRadius: '50%', background: 'var(--blue-700)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                          <svg width="11" height="8" viewBox="0 0 11 8" fill="none"><path d="M1 4l3 3 6-6" stroke="white" strokeWidth="1.8" strokeLinecap="round"/></svg>
                        </div>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </section>

          <div className="responsive-actions">
            <button className="btn btn-secondary" onClick={() => navigate('/staff')}>Back</button>
            <button className="btn btn-primary btn-lg" disabled={!selected} onClick={handleStart}>
              <BookOpen size={16} /> Begin Examination
            </button>
          </div>
          {selected && (
            <p style={{ marginTop: '0.75rem', fontSize: '0.8rem', color: 'var(--gray-300)' }}>
              You selected: <strong>{selected.label}</strong> · Questions are randomly selected as 10 easy, 10 medium, and 5 hard.
            </p>
          )}
        </>
      )}
    </div>
  )
}
