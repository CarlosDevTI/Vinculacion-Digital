# Guía de Configuración del Frontend

Este documento explica los pasos para configurar el entorno de desarrollo de React con Vite y TailwindCSS.

## 1. Inicialización del Proyecto con Vite

Para crear la base de nuestro proyecto React, utilizamos **Vite**. Vite es una herramienta de construcción moderna que ofrece un desarrollo extremadamente rápido.

**Comando:**
```bash
npm create vite@latest . -- --template react
```
- `.` indica que el proyecto se crea en el directorio actual (`frontend`).
- `-- --template react` especifica que queremos usar la plantilla de React.

## 2. Instalación de TailwindCSS

A continuación, instalamos TailwindCSS junto con sus dependencias (`postcss` y `autoprefixer`), que son necesarias para que se integre correctamente con nuestro proceso de construcción.

**Comandos:**
```bash
# Instala las dependencias de desarrollo
npm install -D tailwindcss postcss autoprefixer

# Crea los archivos de configuración de Tailwind
npx tailwindcss init -p
```

## 3. Configuración de TailwindCSS

Una vez instalados los paquetes, necesitamos configurar dos archivos:

### a) `tailwind.config.js`

Este archivo le dice a Tailwind qué archivos debe analizar para encontrar las clases de utilidad que estás usando. Reemplaza el contenido del archivo con lo siguiente:

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

### b) `src/index.css`

Aquí es donde importamos las "capas" base de Tailwind. Borra todo el contenido de este archivo (que viene por defecto con Vite) y reemplázalo con estas tres líneas:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

## 4. Instalar Librería de Iconos

Tu componente utiliza `lucide-react` para los iconos. Lo instalamos con este comando:

**Comando:**
```bash
npm install lucide-react
```

## 5. Integrar el Componente Principal

Para que tu vista `VinculacionView.jsx` sea la página principal, necesitamos modificar el punto de entrada de la aplicación.

### a) Mover el archivo (si es necesario)
Asegúrate de que tu archivo `vinculacionView.jsx` esté en `frontend/src/pages/`.

### b) Modificar `src/main.jsx`

Reemplaza el contenido de `src/main.jsx` con el siguiente código. Esto importa tu componente y el archivo `index.css` con los estilos de Tailwind, y le dice a React que renderice tu vista.

```javascript
import React from 'react'
import ReactDOM from 'react-dom/client'
import VinculacionDigital from './pages/vinculacionView.jsx' // Asegúrate que la ruta sea correcta
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <VinculacionDigital />
  </React.StrictMode>,
)
```

## 6. Iniciar el Servidor de Desarrollo

¡Todo está listo! Ahora puedes iniciar el servidor de desarrollo de Vite.

**Comando:**
```bash
npm run dev
```

Esto iniciará un servidor local (normalmente en `http://localhost:5173`). Abre esa URL en tu navegador para ver tu aplicación funcionando.
