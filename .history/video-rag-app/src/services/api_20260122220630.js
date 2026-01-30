// API Configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

// Store for active abort controllers
const activeRequests = new Map()

// Helper to create a cancellable request
export function createCancellableRequest(key) {
    // Cancel any existing request with the same key
    if (activeRequests.has(key)) {
        activeRequests.get(key).abort()
    }
    const controller = new AbortController()
    activeRequests.set(key, controller)
    return controller
}

// Helper to cancel a request by key
export function cancelRequest(key) {
    if (activeRequests.has(key)) {
        activeRequests.get(key).abort()
        activeRequests.delete(key)
    }
}

// Helper function for API calls with optional AbortSignal
async function apiCall(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`

    const config = {
        headers: {
            'Content-Type': 'application/json',
            ...options.headers,
        },
        ...options,
    }

    // Remove Content-Type for FormData (file uploads)
    if (options.body instanceof FormData) {
        delete config.headers['Content-Type']
    }

    try {
        const response = await fetch(url, config)

        if (!response.ok) {
            const error = await response.json().catch(() => ({ message: 'Request failed' }))
            throw new Error(error.message || `HTTP ${response.status}`)
        }

        return await response.json()
    } catch (error) {
        // Don't log abort errors as they're intentional
        if (error.name === 'AbortError') {
            throw error
        }
        console.error(`API Error [${endpoint}]:`, error)
        throw error
    }
}

// ============================================
// VIDEO API
// ============================================

export const videoAPI = {
    // Get all videos
    getAll: () => apiCall('/videos'),

    // Get single video by ID
    getById: (id) => apiCall(`/videos/${id}`),

    // Process video from URL (YouTube, etc.)
    processUrl: (url, title) => apiCall('/videos/process-url', {
        method: 'POST',
        body: JSON.stringify({ url, title }),
    }),

    // Toggle like
    toggleLike: (id) => apiCall(`/videos/${id}/like`, { method: 'POST' }),

    // Upload video file
    upload: (file, title, onProgress) => {
        const formData = new FormData()
        formData.append('file', file)
        formData.append('title', title || file.name)

        return apiCall('/videos/upload', {
            method: 'POST',
            body: formData,
        })
    },

    // Get video processing status
    getStatus: (id) => apiCall(`/videos/${id}/status`),

    // Delete video
    delete: (id) => apiCall(`/videos/${id}`, { method: 'DELETE' }),

    // Get video transcript
    getTranscript: (id) => apiCall(`/videos/${id}/transcript`),

    // Get video notes
    getNotes: (id) => apiCall(`/videos/${id}/notes`),

    // Create a note
    createNote: (videoId, content, timestamp) => apiCall(`/videos/${videoId}/notes`, {
        method: 'POST',
        body: JSON.stringify({ content, timestamp }),
    }),

    // Delete a note
    deleteNote: (videoId, noteId) => apiCall(`/videos/${videoId}/notes/${noteId}`, { method: 'DELETE' }),
}

// ============================================
// CHAT API (RAG)
// ============================================

export const chatAPI = {
    // Send message to AI about a video
    sendMessage: (videoId, message) => apiCall('/chat', {
        method: 'POST',
        body: JSON.stringify({ videoId, message }),
    }),

    // Get chat history for a video
    getHistory: (videoId) => apiCall(`/chat/${videoId}/history`),

    // Clear chat history
    clearHistory: (videoId) => apiCall(`/chat/${videoId}/history`, { method: 'DELETE' }),
}

// ============================================
// QUIZ API
// ============================================

export const quizAPI = {
    // Generate quiz for a video
    generate: (videoId, questionCount = 10) => apiCall('/quiz/generate', {
        method: 'POST',
        body: JSON.stringify({ videoId, questionCount }),
    }),

    // Get quiz by ID
    getById: (quizId) => apiCall(`/quiz/${quizId}`),

    // Submit quiz answers
    submit: (quizId, answers) => apiCall(`/quiz/${quizId}/submit`, {
        method: 'POST',
        body: JSON.stringify({ answers }),
    }),

    // Get quiz results/analysis
    getResults: (quizId) => apiCall(`/quiz/${quizId}/results`),
}

// ============================================
// SEARCH API
// ============================================

export const searchAPI = {
    // Search across all videos
    search: (query, filters = {}) => apiCall('/search', {
        method: 'POST',
        body: JSON.stringify({ query, ...filters }),
    }),

    // Get search suggestions
    suggestions: (query) => apiCall(`/search/suggestions?q=${encodeURIComponent(query)}`),
}

export default {
    video: videoAPI,
    chat: chatAPI,
    quiz: quizAPI,
    search: searchAPI,
}
