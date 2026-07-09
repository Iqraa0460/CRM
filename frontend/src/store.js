import { configureStore, createSlice, createAsyncThunk } from '@reduxjs/toolkit';

const API_BASE = 'http://127.0.0.1:8000/api';

// Async Thunks
export const fetchMetadata = createAsyncThunk(
  'crm/fetchMetadata',
  async (_, { rejectWithValue }) => {
    try {
      const [hcpsRes, matsRes, sampsRes] = await Promise.all([
        fetch(`${API_BASE}/hcps`),
        fetch(`${API_BASE}/materials`),
        fetch(`${API_BASE}/samples`),
      ]);
      const hcps = await hcpsRes.json();
      const materials = await matsRes.json();
      const samples = await sampsRes.json();
      return { hcps, materials, samples };
    } catch (err) {
      return rejectWithValue(err.message || 'Failed to fetch catalog and metadata.');
    }
  }
);

export const fetchInteractions = createAsyncThunk(
  'crm/fetchInteractions',
  async (_, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/interactions`);
      return await res.json();
    } catch (err) {
      return rejectWithValue(err.message || 'Failed to fetch interaction logs.');
    }
  }
);

export const sendChatMessage = createAsyncThunk(
  'crm/sendChatMessage',
  async ({ message, currentForm }, { rejectWithValue, dispatch }) => {
    try {
      // Structure state to match backend expectation
      // Materials should be names string list
      const materialsMapped = currentForm.materials.map(m => m.name);
      // Samples should be {name, quantity} dict list
      const samplesMapped = currentForm.samples.map(s => ({
        name: s.name,
        quantity: s.quantity
      }));

      const payload = {
        message,
        current_state: {
          interaction_id: currentForm.interactionId || null,
          hcp_name: currentForm.hcpName,
          hcp_id: currentForm.hcpId,
          type: currentForm.type,
          date: currentForm.date,
          time: currentForm.time,
          attendees: currentForm.attendees,
          topics_discussed: currentForm.topicsDiscussed,
          outcomes: currentForm.outcomes,
          follow_up_actions: currentForm.followUpActions,
          observed_sentiment: currentForm.observedSentiment,
          materials: materialsMapped,
          samples: samplesMapped
        },
        session_id: 'rep-session-1'
      };

      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      
      if (!res.ok) throw new Error('API server error');
      
      const data = await res.json();
      
      // If the interaction was logged via chat, reload logs
      if (data.logged) {
        dispatch(fetchInteractions());
        dispatch(fetchMetadata()); // Refresh stock levels
      }
      
      return data;
    } catch (err) {
      return rejectWithValue(err.message || 'Failed to get AI assistant response.');
    }
  }
);

export const submitFormInteraction = createAsyncThunk(
  'crm/submitFormInteraction',
  async (currentForm, { rejectWithValue, dispatch }) => {
    try {
      const payload = {
        hcp_id: currentForm.hcpId,
        hcp_name: currentForm.hcpName,
        type: currentForm.type,
        date: currentForm.date,
        time: currentForm.time,
        attendees: currentForm.attendees,
        topics_discussed: currentForm.topicsDiscussed,
        outcomes: currentForm.outcomes,
        follow_up_actions: currentForm.followUpActions,
        observed_sentiment: currentForm.observedSentiment,
        materials: currentForm.materials.map(m => m.id),
        samples: currentForm.samples.map(s => ({
          sample_id: s.id,
          quantity: s.quantity
        }))
      };

      const res = await fetch(`${API_BASE}/interactions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) throw new Error('Failed to save log');
      
      const loggedData = await res.json();
      dispatch(fetchInteractions());
      dispatch(fetchMetadata()); // Refresh stocks
      return loggedData;
    } catch (err) {
      return rejectWithValue(err.message || 'Failed to log interaction.');
    }
  }
);

const initialFormState = {
  interactionId: null,
  hcpName: '',
  hcpId: null,
  type: 'Meeting',
  date: new Date().toISOString().split('T')[0],
  time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false }),
  attendees: [],
  topicsDiscussed: '',
  outcomes: '',
  followUpActions: '',
  observedSentiment: 'Neutral',
  materials: [], // List of material objects {id, name, type}
  samples: [] // List of sample objects {id, name, quantity, stock}
};

const crmSlice = createSlice({
  name: 'crm',
  initialState: {
    hcps: [],
    materialsCatalog: [],
    samplesCatalog: [],
    currentForm: initialFormState,
    chatMessages: [
      {
        id: 'init',
        sender: 'agent',
        text: "Log interaction details here (e.g., 'Met Dr. Smith, discussed Product X efficacy, positive sentiment, shared brochure') or ask for help.",
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }
    ],
    suggestions: [],
    interactionLogs: [],
    loading: false,
    chatLoading: false,
    error: null,
    submitSuccess: false
  },
  reducers: {
    setFormValue: (state, action) => {
      const { key, value } = action.payload;
      state.currentForm[key] = value;
    },
    addAttendee: (state, action) => {
      const name = action.payload.trim();
      if (name && !state.currentForm.attendees.includes(name)) {
        state.currentForm.attendees.push(name);
      }
    },
    removeAttendee: (state, action) => {
      state.currentForm.attendees = state.currentForm.attendees.filter(
        name => name !== action.payload
      );
    },
    addMaterialById: (state, action) => {
      const matId = parseInt(action.payload);
      const material = state.materialsCatalog.find(m => m.id === matId);
      if (material && !state.currentForm.materials.some(m => m.id === matId)) {
        state.currentForm.materials.push(material);
      }
    },
    addMaterialByName: (state, action) => {
      const matName = action.payload;
      const material = state.materialsCatalog.find(m => m.name.toLowerCase() === matName.toLowerCase());
      if (material && !state.currentForm.materials.some(m => m.id === material.id)) {
        state.currentForm.materials.push(material);
      }
    },
    removeMaterial: (state, action) => {
      state.currentForm.materials = state.currentForm.materials.filter(
        m => m.id !== action.payload
      );
    },
    addSampleById: (state, action) => {
      const { id, quantity } = action.payload;
      const sample = state.samplesCatalog.find(s => s.id === id);
      if (sample && !state.currentForm.samples.some(s => s.id === id)) {
        state.currentForm.samples.push({
          ...sample,
          quantity: quantity || 1
        });
      }
    },
    updateSampleQty: (state, action) => {
      const { id, quantity } = action.payload;
      const existing = state.currentForm.samples.find(s => s.id === id);
      if (existing) {
        existing.quantity = Math.max(1, parseInt(quantity) || 1);
      }
    },
    removeSample: (state, action) => {
      state.currentForm.samples = state.currentForm.samples.filter(
        s => s.id !== action.payload
      );
    },
    clearForm: (state) => {
      state.currentForm = {
        ...initialFormState,
        date: new Date().toISOString().split('T')[0],
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false })
      };
      state.suggestions = [];
      state.submitSuccess = false;
    },
    addManualChatMessage: (state, action) => {
      state.chatMessages.push({
        id: Date.now().toString(),
        sender: action.payload.sender, // 'user' or 'agent'
        text: action.payload.text,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      });
    },
    addSuggestedFollowUpToForm: (state, action) => {
      const text = action.payload;
      const current = state.currentForm.followUpActions;
      if (current) {
        if (!current.includes(text)) {
          state.currentForm.followUpActions = `${current}\n- ${text}`;
        }
      } else {
        state.currentForm.followUpActions = `- ${text}`;
      }
    },
    resetSuccess: (state) => {
      state.submitSuccess = false;
    }
  },
  extraReducers: (builder) => {
    builder
      // fetchMetadata
      .addCase(fetchMetadata.pending, (state) => {
        state.loading = true;
      })
      .addCase(fetchMetadata.fulfilled, (state, action) => {
        state.loading = false;
        state.hcps = action.payload.hcps;
        state.materialsCatalog = action.payload.materials;
        state.samplesCatalog = action.payload.samples;
      })
      .addCase(fetchMetadata.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })

      // fetchInteractions
      .addCase(fetchInteractions.fulfilled, (state, action) => {
        state.interactionLogs = action.payload;
      })

      // sendChatMessage
      .addCase(sendChatMessage.pending, (state) => {
        state.chatLoading = true;
      })
      .addCase(sendChatMessage.fulfilled, (state, action) => {
        state.chatLoading = false;
        const data = action.payload;
        
        // 1. Add agent reply to chat messages
        state.chatMessages.push({
          id: Date.now().toString(),
          sender: 'agent',
          text: data.reply,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        });
        
        // 2. Synchronize extracted state back to currentForm
        if (data.updated_state) {
          const u = data.updated_state;
          
          if (u.hcp_name) {
            state.currentForm.hcpName = u.hcp_name;
            state.currentForm.hcpId = u.hcp_id || null;
          }
          if (u.type) state.currentForm.type = u.type;
          if (u.date) state.currentForm.date = u.date;
          if (u.time) state.currentForm.time = u.time;
          if (u.attendees) state.currentForm.attendees = u.attendees;
          if (u.topics_discussed) state.currentForm.topicsDiscussed = u.topics_discussed;
          if (u.outcomes) state.currentForm.outcomes = u.outcomes;
          if (u.follow_up_actions) state.currentForm.followUpActions = u.follow_up_actions;
          if (u.observed_sentiment) state.currentForm.observedSentiment = u.observed_sentiment;
          
          // Map material names back to material objects in catalog
          if (u.materials) {
            state.currentForm.materials = [];
            u.materials.forEach(matName => {
              const matched = state.materialsCatalog.find(m => m.name.toLowerCase() === matName.toLowerCase());
              if (matched) state.currentForm.materials.push(matched);
            });
          }
          
          // Map sample dicts back to sample objects with quantity
          if (u.samples) {
            state.currentForm.samples = [];
            u.samples.forEach(sInfo => {
              const matched = state.samplesCatalog.find(s => s.name.toLowerCase() === sInfo.name.toLowerCase());
              if (matched) {
                state.currentForm.samples.push({
                  ...matched,
                  quantity: sInfo.quantity
                });
              }
            });
          }
        }
        
        // 3. Update suggested follow-ups list
        if (data.suggestions) {
          state.suggestions = data.suggestions;
        }

        if (data.logged) {
          // Keep form populated so user can review and issue corrections
          state.currentForm.interactionId = data.logged_id;
          state.submitSuccess = true;
        }
      })
      .addCase(sendChatMessage.rejected, (state, action) => {
        state.chatLoading = false;
        state.chatMessages.push({
          id: Date.now().toString(),
          sender: 'agent',
          text: `Error contacting the AI agent: ${action.payload}. Please check if the FastAPI backend is running.`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        });
      })

      // submitFormInteraction
      .addCase(submitFormInteraction.pending, (state) => {
        state.loading = true;
      })
      .addCase(submitFormInteraction.fulfilled, (state) => {
        state.loading = false;
        state.submitSuccess = true;
        // reset form state
        state.currentForm = {
          ...initialFormState,
          date: new Date().toISOString().split('T')[0],
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false })
        };
        state.suggestions = [];
      })
      .addCase(submitFormInteraction.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      });
  }
});

export const {
  setFormValue,
  addAttendee,
  removeAttendee,
  addMaterialById,
  addMaterialByName,
  removeMaterial,
  addSampleById,
  updateSampleQty,
  removeSample,
  clearForm,
  addManualChatMessage,
  addSuggestedFollowUpToForm,
  resetSuccess
} = crmSlice.actions;

export const store = configureStore({
  reducer: {
    crm: crmSlice.reducer
  }
});
export default store;
