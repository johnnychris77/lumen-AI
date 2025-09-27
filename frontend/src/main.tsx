import React from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'

function Home(){ return <div style={{padding:24}}><h2>LumenAI</h2><p>It works 🎉</p><p><Link to="/health">API health</Link></p></div> }
function Health(){ return <iframe src="/api/health" style={{width:'100%',height:200,border:'1px solid #ddd'}} /> }

const App = () => (
  <BrowserRouter>
    <Routes>
      <Route path="/" element={<Home/>} />
      <Route path="/health" element={<Health/>} />
    </Routes>
  </BrowserRouter>
)

createRoot(document.getElementById('root')!).render(<App/>)
