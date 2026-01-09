//? 1. Importa las librerías necesarias
import React from 'react'
import ReactDOM from 'react-dom/client'
//? 2. Importa tu componente principal
import App from './App.jsx'
import './index.css'

//? 3. Busca el div 'root' del index.html y le dice a React que tome control de él.
ReactDOM.createRoot(document.getElementById('root')).render(
  //? 4. Le ordena a React que "dibuje" (renderice) el componente <App /> dentro de ese div.
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
