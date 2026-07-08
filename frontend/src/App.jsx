import React, { useEffect, useState, useRef } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { 
  Users, MessageSquare, Calendar, Clock, Smile, FileText, CheckCircle, 
  Send, RotateCcw, Trash2, Plus, Sparkles, Mic, Search, AlertCircle
} from 'lucide-react';
import { 
  fetchMetadata, fetchInteractions, setFormValue, addAttendee, removeAttendee,
  addMaterialById, removeMaterial, addSampleById, updateSampleQty, removeSample,
  clearForm, sendChatMessage, submitFormInteraction, addSuggestedFollowUpToForm,
  resetSuccess, addManualChatMessage
} from './store';

function App() {
  const dispatch = useDispatch();
  
  // Redux State selectors
  const { 
    hcps, materialsCatalog, samplesCatalog, currentForm, chatMessages, 
    suggestions, interactionLogs, loading, chatLoading, error, submitSuccess 
  } = useSelector(state => state.crm);

  // Component UI state
  const [chatInput, setChatInput] = useState('');
  const [hcpSearch, setHcpSearch] = useState('');
  const [showHcpDropdown, setShowHcpDropdown] = useState(false);
  const [attendeeInput, setAttendeeInput] = useState('');
  
  const [materialSearch, setMaterialSearch] = useState('');
  const [showMaterialDropdown, setShowMaterialDropdown] = useState(false);
  
  const [sampleSelectId, setSampleSelectId] = useState('');
  const [sampleSelectQty, setSampleSelectQty] = useState(1);
  
  const [isRecording, setIsRecording] = useState(false);
  const [recordingStatus, setRecordingStatus] = useState('');

  const chatEndRef = useRef(null);

  // Load database metadata and logs on mount
  useEffect(() => {
    dispatch(fetchMetadata());
    dispatch(fetchInteractions());
  }, [dispatch]);

  // Scroll to bottom of chat whenever messages change
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  // Reset success flag after 5 seconds
  useEffect(() => {
    if (submitSuccess) {
      const timer = setTimeout(() => {
        dispatch(resetSuccess());
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [submitSuccess, dispatch]);

  // Event Handlers for Left Form
  const handleFormChange = (key, value) => {
    dispatch(setFormValue({ key, value }));
  };

  const handleSelectHcp = (hcp) => {
    dispatch(setFormValue({ key: 'hcpName', value: hcp.name }));
    dispatch(setFormValue({ key: 'hcpId', value: hcp.id }));
    setHcpSearch(hcp.name);
    setShowHcpDropdown(false);
  };

  const handleAddAttendee = (e) => {
    if (e.key === 'Enter' && attendeeInput.trim()) {
      e.preventDefault();
      dispatch(addAttendee(attendeeInput));
      setAttendeeInput('');
    }
  };

  const handleAddMaterial = (matId) => {
    if (matId) {
      dispatch(addMaterialById(matId));
      setMaterialSearch('');
      setShowMaterialDropdown(false);
    }
  };

  const handleAddSample = () => {
    if (sampleSelectId) {
      dispatch(addSampleById({ id: parseInt(sampleSelectId), quantity: sampleSelectQty }));
      setSampleSelectId('');
      setSampleSelectQty(1);
    }
  };

  const handleVoiceSummarization = () => {
    setIsRecording(true);
    setRecordingStatus('Listening to voice note (3s)...');
    
    setTimeout(() => {
      setRecordingStatus('Transcribing voice note...');
      setTimeout(() => {
        // Simulated voice note text
        const simulatedTranscription = 
          "Met Dr. Anita Sharma today at 10 AM. Discussed OncoBoost Phase III PDF efficacy and trial outcomes. " +
          "She requested 2 samples of OncoBoost 10mg Starter Kit. Sentiment was positive.";
        
        setIsRecording(false);
        setRecordingStatus('');
        
        // Log user voice prompt to chat and trigger AI agent extraction
        dispatch(addManualChatMessage({ sender: 'user', text: `[Voice Note]: ${simulatedTranscription}` }));
        dispatch(sendChatMessage({ message: simulatedTranscription, currentForm }));
      }, 1000);
    }, 2000);
  };

  const handleSubmitLog = (e) => {
    e.preventDefault();
    if (!currentForm.hcpName) {
      alert("Please search or select a Healthcare Professional (HCP) first.");
      return;
    }
    dispatch(submitFormInteraction(currentForm));
  };

  const handleClear = () => {
    dispatch(clearForm());
    setHcpSearch('');
  };

  // Event Handlers for Chat Panel
  const handleChatSubmit = (e) => {
    e.preventDefault();
    if (!chatInput.trim()) return;
    
    const userMsg = chatInput.trim();
    dispatch(addManualChatMessage({ sender: 'user', text: userMsg }));
    setChatInput('');
    
    dispatch(sendChatMessage({ message: userMsg, currentForm }));
  };

  // Autocomplete filtering
  const filteredHcps = hcps.filter(h => 
    h.name.toLowerCase().includes(hcpSearch.toLowerCase()) ||
    h.specialty.toLowerCase().includes(hcpSearch.toLowerCase())
  );

  const filteredMaterials = materialsCatalog.filter(m => 
    m.name.toLowerCase().includes(materialSearch.toLowerCase()) &&
    !currentForm.materials.some(added => added.id === m.id)
  );

  return (
    <div className="app-container">
      <div className="glow-bg"></div>
      <div className="glow-bg-2"></div>
      
      {/* Header */}
      <header className="app-header">
        <div className="header-title-group">
          <h1>
            <Sparkles className="w-6 h-6 text-indigo-400" />
            AI-First CRM
          </h1>
          <p>Healthcare Professional (HCP) Interaction Portal</p>
        </div>
        <div className="rep-badge">
          Field Rep Mode
        </div>
      </header>

      {/* Success Notification */}
      {submitSuccess && (
        <div className="toast-success">
          <CheckCircle className="w-5 h-5 text-emerald-400" />
          <span>Interaction successfully saved to CRM database!</span>
        </div>
      )}

      {/* Main Layout Grid */}
      <div className="grid-layout">
        
        {/* Left Column: Form Details */}
        <div className="column-left">
          <form className="panel" onSubmit={handleSubmitLog}>
            <div className="panel-title">
              <FileText className="w-5 h-5 text-indigo-400" />
              Interaction Details
              <span>Fill fields or type in Chat on the right</span>
            </div>

            <div className="form-grid">
              
              {/* HCP Name */}
              <div className="form-group search-dropdown-container">
                <label>HCP Name</label>
                <div className="input-container">
                  <Search className="input-icon-left w-4 h-4" />
                  <input 
                    type="text" 
                    placeholder="Search or select HCP..."
                    value={hcpSearch || currentForm.hcpName}
                    readOnly
                    disabled
                  />
                </div>
                {showHcpDropdown && hcpSearch && (
                  <div className="search-results-dropdown">
                    {filteredHcps.length > 0 ? (
                      filteredHcps.map(h => (
                        <div 
                          key={h.id} 
                          className="search-result-item"
                          onClick={() => handleSelectHcp(h)}
                        >
                          <span className="search-result-title">{h.name}</span>
                          <span className="search-result-sub">{h.specialty} • {h.clinic}</span>
                        </div>
                      ))
                    ) : (
                      <div className="p-3 text-xs text-gray-400">No HCPs found.</div>
                    )}
                  </div>
                )}
              </div>

              {/* Interaction Type */}
              <div className="form-group">
                <label>Interaction Type</label>
                <select 
                  value={currentForm.type} 
                  disabled
                >
                  <option value="Meeting">Meeting</option>
                  <option value="Call">Call</option>
                  <option value="Email">Email</option>
                  <option value="Presentation">Presentation</option>
                </select>
              </div>

              {/* Date */}
              <div className="form-group">
                <label>Date</label>
                <div className="input-container">
                  <Calendar className="input-icon-left w-4 h-4" />
                  <input 
                    type="date" 
                    value={currentForm.date} 
                    readOnly
                    disabled
                  />
                </div>
              </div>

              {/* Time */}
              <div className="form-group">
                <label>Time</label>
                <div className="input-container">
                  <Clock className="input-icon-left w-4 h-4" />
                  <input 
                    type="text" 
                    placeholder="19:36"
                    value={currentForm.time} 
                    readOnly
                    disabled
                  />
                </div>
              </div>

              {/* Attendees */}
              <div className="form-group full-width">
                <label>Attendees</label>
                <input 
                  type="text" 
                  placeholder="Enter names and press Enter..." 
                  value={attendeeInput}
                  readOnly
                  disabled
                />
                {currentForm.attendees.length > 0 && (
                  <div className="flex flex-wrap gap-2 mt-2" style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '8px' }}>
                    {currentForm.attendees.map(name => (
                      <span key={name} className="log-tag" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                        {name}
                        <button 
                          type="button" 
                          className="btn-remove" 
                          onClick={() => dispatch(removeAttendee(name))}
                        >
                          ×
                        </button>
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Topics Discussed */}
              <div className="form-group full-width">
                <label>Topics Discussed</label>
                <textarea 
                  placeholder="Enter key discussion points..."
                  value={currentForm.topicsDiscussed}
                  readOnly
                  disabled
                />
                
                {/* Voice Note Summarizer */}
                <button 
                  type="button" 
                  className={`btn-voice ${isRecording ? 'transcribing' : ''}`}
                  onClick={handleVoiceSummarization}
                  disabled={isRecording}
                >
                  <Mic className="w-4 h-4" />
                  {isRecording ? recordingStatus : 'Summarize from Voice Note (Requires Consent)'}
                </button>
              </div>

              {/* Materials Shared */}
              <div className="form-group full-width form-section">
                <h3>Materials Shared / Samples Distributed</h3>
                <label style={{ marginBottom: '6px', display: 'block' }}>Materials Shared</label>
                <div className="search-dropdown-container" style={{ marginBottom: '12px' }}>
                  <div className="input-container">
                    <Search className="input-icon-left w-4 h-4" />
                    <input 
                      type="text" 
                      placeholder="Search/Add clinical brochures..."
                      value={materialSearch}
                      readOnly
                      disabled
                    />
                  </div>
                  {showMaterialDropdown && materialSearch && (
                    <div className="search-results-dropdown">
                      {filteredMaterials.length > 0 ? (
                        filteredMaterials.map(m => (
                          <div 
                            key={m.id} 
                            className="search-result-item"
                            onClick={() => handleAddMaterial(m.id)}
                          >
                            <span className="search-result-title">{m.name}</span>
                            <span className="search-result-sub">{m.type}</span>
                          </div>
                        ))
                      ) : (
                        <div className="p-3 text-xs text-gray-400">No new materials found.</div>
                      )}
                    </div>
                  )}
                </div>

                {/* Added Materials List */}
                {currentForm.materials.length > 0 ? (
                  currentForm.materials.map(m => (
                    <div key={m.id} className="catalog-item-row">
                      <div>
                        <span className="catalog-item-name">{m.name}</span>
                        <span className="catalog-item-meta" style={{ marginLeft: '8px' }}>({m.type})</span>
                      </div>
                      <button 
                        type="button" 
                        className="btn-remove" 
                        onClick={() => dispatch(removeMaterial(m.id))}
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  ))
                ) : (
                  <div className="text-xs text-gray-500 italic p-2 border border-dashed border-gray-800 rounded mb-3">No materials added.</div>
                )}
              </div>

              {/* Samples Distributed */}
              <div className="form-group full-width">
                <label style={{ marginBottom: '6px', display: 'block' }}>Samples Distributed</label>
                <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
                  <select 
                    style={{ flexGrow: 1 }}
                    value={sampleSelectId} 
                    disabled
                  >
                    <option value="">Select Drug Sample...</option>
                    {samplesCatalog.map(s => (
                      <option key={s.id} value={s.id}>
                        {s.name} (Stock: {s.stock})
                      </option>
                    ))}
                  </select>
                  <input 
                    type="number" 
                    className="qty-input"
                    value={sampleSelectQty} 
                    min="1"
                    disabled
                  />
                  <button 
                    type="button" 
                    className="btn-secondary" 
                    disabled
                  >
                    <Plus className="w-4 h-4" /> Add
                  </button>
                </div>

                {/* Added Samples List */}
                {currentForm.samples.length > 0 ? (
                  currentForm.samples.map(s => (
                    <div key={s.id} className="catalog-item-row">
                      <div>
                        <span className="catalog-item-name">{s.name}</span>
                        <span className="catalog-item-meta" style={{ marginLeft: '8px' }}>(Available stock: {s.stock})</span>
                      </div>
                      <div className="catalog-actions">
                        <label style={{ fontSize: '10px' }}>QTY</label>
                        <input 
                          type="number" 
                          className="qty-input" 
                          value={s.quantity} 
                          min="1"
                          max={s.stock}
                          onChange={(e) => dispatch(updateSampleQty({ id: s.id, quantity: parseInt(e.target.value) || 1 }))}
                        />
                        <button 
                          type="button" 
                          className="btn-remove" 
                          onClick={() => dispatch(removeSample(s.id))}
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-xs text-gray-500 italic p-2 border border-dashed border-gray-800 rounded">No samples added.</div>
                )}
              </div>

              {/* Observed HCP Sentiment */}
              <div className="form-group full-width form-section">
                <label>Observed/Inferred HCP Sentiment</label>
                <div className="sentiment-group">
                  {[
                    { val: 'Positive', emoji: '😊', class: 'positive' },
                    { val: 'Neutral', emoji: '😐', class: 'neutral' },
                    { val: 'Negative', emoji: '😟', class: 'negative' }
                  ].map(item => (
                    <button
                      key={item.val}
                      type="button"
                      className={`sentiment-btn ${currentForm.observedSentiment === item.val ? `active ${item.class}` : ''}`}
                      disabled
                    >
                      <span className="emoji">{item.emoji}</span>
                      <span className="label">{item.val}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Outcomes */}
              <div className="form-group full-width">
                <label>Outcomes</label>
                <textarea 
                  placeholder="Key outcomes or agreements..."
                  value={currentForm.outcomes}
                  readOnly
                  disabled
                />
              </div>

              {/* Follow-up Actions */}
              <div className="form-group full-width">
                <label>Follow-up Actions</label>
                <textarea 
                  placeholder="Enter next steps or tasks..."
                  value={currentForm.followUpActions}
                  readOnly
                  disabled
                />
              </div>

            </div>

            {/* AI Suggested Follow-ups */}
            {suggestions.length > 0 && (
              <div className="form-group full-width" style={{ marginTop: '8px' }}>
                <label style={{ color: '#818cf8', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <Sparkles className="w-3.5 h-3.5" />
                  AI Suggested Follow-ups:
                </label>
                <div className="suggestions-list">
                  {suggestions.map(s => (
                    <button
                      key={s}
                      type="button"
                      className="suggestion-item"
                      onClick={() => dispatch(addSuggestedFollowUpToForm(s))}
                    >
                      <span className="plus-icon">+</span>
                      <span>{s}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Action Row */}
            <div className="form-actions-row">
              <button 
                type="button" 
                className="btn-secondary" 
                onClick={handleClear}
                disabled={loading}
              >
                <RotateCcw className="w-4 h-4 mr-2" style={{ display: 'inline' }} />
                Reset
              </button>
              <button 
                type="submit" 
                className="btn-primary" 
                disabled={loading}
              >
                <CheckCircle className="w-4 h-4 mr-2" style={{ display: 'inline' }} />
                {loading ? 'Logging...' : 'Log'}
              </button>
            </div>
          </form>
        </div>

        {/* Right Column: AI Assistant Chat */}
        <div className="column-right">
          <div className="panel">
            <div className="panel-title">
              <MessageSquare className="w-5 h-5 text-purple-400" />
              AI Assistant
              <span>Log interaction via chat</span>
            </div>

            <div className="chat-container">
              
              {/* Chat Message Logs */}
              <div className="chat-messages">
                {chatMessages.map(msg => (
                  <div key={msg.id} className={`chat-message ${msg.sender}`}>
                    <div className="message-bubble">
                      {msg.text}
                    </div>
                    <span className="message-meta">{msg.timestamp}</span>
                  </div>
                ))}
                {chatLoading && (
                  <div className="chat-message agent">
                    <div className="message-bubble" style={{ fontStyle: 'italic', color: 'var(--text-secondary)' }}>
                      Analyzing interaction transcript...
                    </div>
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>

              {/* Chat Input form */}
              <form className="chat-input-form" onSubmit={handleChatSubmit}>
                <input 
                  type="text" 
                  className="chat-input"
                  placeholder="Describe interaction..."
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  disabled={chatLoading}
                />
                <button 
                  type="submit" 
                  className="btn-primary" 
                  disabled={chatLoading || !chatInput.trim()}
                >
                  <Send className="w-4 h-4" /> Send
                </button>
              </form>

            </div>
          </div>
        </div>

      </div>

      {/* Database History Table */}
      <section className="logs-section">
        <h2>
          <Users className="w-5 h-5 text-indigo-400" />
          HCP Interaction History Logs (Database View)
        </h2>
        
        <div className="logs-table-wrapper">
          {interactionLogs.length > 0 ? (
            <table className="logs-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>HCP Name</th>
                  <th>Type</th>
                  <th>Date & Time</th>
                  <th>Topics Discussed</th>
                  <th>Materials Shared</th>
                  <th>Samples Sent</th>
                  <th>Sentiment</th>
                  <th>Follow-ups</th>
                </tr>
              </thead>
              <tbody>
                {interactionLogs.map(log => (
                  <tr key={log.id}>
                    <td style={{ fontWeight: 'bold', color: 'var(--accent-color)' }}>#{log.id}</td>
                    <td>
                      <div>{log.hcp ? log.hcp.name : 'Unknown HCP'}</div>
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                        {log.hcp ? log.hcp.specialty : ''}
                      </div>
                    </td>
                    <td>
                      <span className="log-tag">{log.type}</span>
                    </td>
                    <td>
                      <div>{log.date}</div>
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{log.time}</div>
                    </td>
                    <td style={{ maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={log.topics_discussed}>
                      {log.topics_discussed || '-'}
                    </td>
                    <td>
                      {log.materials.length > 0 ? (
                        log.materials.map(m => (
                          <span key={m.id} className="log-tag">{m.name}</span>
                        ))
                      ) : '-'}
                    </td>
                    <td>
                      {log.samples.length > 0 ? (
                        log.samples.map(s => (
                          <span key={s.sample.id} className="log-tag">{s.sample.name} (Qty: {s.quantity})</span>
                        ))
                      ) : '-'}
                    </td>
                    <td>
                      <span className={`sentiment-badge ${log.observed_sentiment.toLowerCase()}`}>
                        {log.observed_sentiment === 'Positive' ? '😊 ' : log.observed_sentiment === 'Negative' ? '😟 ' : '😐 '}
                        {log.observed_sentiment}
                      </span>
                    </td>
                    <td>
                      {log.suggested_followups.length > 0 ? (
                        <ul style={{ margin: 0, paddingLeft: '14px', fontSize: '11px' }}>
                          {log.suggested_followups.map((s, idx) => (
                            <li key={idx}>{s}</li>
                          ))}
                        </ul>
                      ) : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="text-center p-8 text-sm text-gray-500 italic">No logged interactions found in database. Create one using the form or chat!</div>
          )}
        </div>
      </section>
    </div>
  );
}

export default App;
