import React from 'react';
//? 1. IMPORTACIÓN: Le decimos a JavaScript "trae el código que se exporta desde esta ruta".
//? La variable 'VinculacionDigital' ahora contiene tu componente.
import VinculacionDigital from './pages/vinculacionView.jsx';

function App() {
  //? 2. RENDERIZADO: En lugar de retornar un simple "Hola Mundo", ahora retorna
  //? el componente que importamos.
  return (
    <VinculacionDigital />
  );
}

export default App;
