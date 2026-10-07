import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import '@fontsource/press-start-2p/400.css'
import '@fontsource/vt323/400.css'
import '@fontsource/inter/400.css'
import '@fontsource/inter/600.css'
import '@fontsource/inter/700.css'
import './index.css'
import App from './App.tsx'
import { AuthProvider } from './auth'
import { ChatUiProvider } from './chatUi'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <ChatUiProvider>
          <App />
        </ChatUiProvider>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
)
