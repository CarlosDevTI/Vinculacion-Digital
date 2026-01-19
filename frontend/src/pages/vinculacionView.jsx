import React, { useState, useEffect } from 'react';
import { CheckCircle, AlertCircle, Loader2, UserCheck, ExternalLink, Building2, X } from 'lucide-react';
import logo from '../assets/LogoHD.png';
import whatsappIcon from '../assets/whatsapp.svg';
import facebookIcon from '../assets/facebook.svg';
import tiktokIcon from '../assets/tiktok.svg';
import youtubeIcon from '../assets/youtube.svg';

const VinculacionDigital = () => {
  const [paso, setPaso] = useState(1);
  const [preregistroId, setPreregistroId] = useState(null);
  const [datosBasicos, setDatosBasicos] = useState({
    nombres_completos: '',
    numero_cedula: '',
    fecha_expedicion: '',
    agencia: '',
    tipo_documento: ''
  });
  const [estadoBiometria, setEstadoBiometria] = useState('PENDIENTE');
  const [loading, setLoading] = useState(false);
  const [notification, setNotification] = useState({ message: '', show: false });
  const [modal, setModal] = useState({ show: false, title: '', message: '' });
  const [linkLinix, setLinkLinix] = useState('');
  const [linkBiometria, setLinkBiometria] = useState('');
  const [verificacionFinalizada, setVerificacionFinalizada] = useState(false);

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
  
  // DESCOMENTAR cuando tengas el enlace real del proveedor:
  // const LINK_BIOMETRIA = 'https://proveedor-real.com/validacion';
  const LINK_BIOMETRIA = null; // null = modo desarrollo

  const AGENCIAS_DISPONIBLES = [
    { key: "PRINCIPAL", nombre: "Principal" },
    { key: "POPULAR", nombre: "Popular" },
    { key: "MONTECARLO", nombre: "Montecarlo" },
    { key: "PORFIA", nombre: "Porfia" },
    { key: "CATAMA", nombre: "Catama" },
    { key: "ACACIAS", nombre: "Acacias" },
    { key: "GRANADA", nombre: "Granada" },
    { key: "GUAYABETAL", nombre: "Guayabetal" },
    { key: "BARRANCA", nombre: "Barranca" },
    { key: "PUERTO_GAITAN", nombre: "Puerto Gaitán" },
    { key: "CABUYARO", nombre: "Cabuyaro" },
    { key: "VISTAHERMOSA", nombre: "Vistahermosa" },
    { key: "PUERTO_LOPEZ", nombre: "Puerto López" },
    { key: "EL_CASTILLO", nombre: "El Castillo" },
    { key: "CUMARAL", nombre: "Cumaral" },
    { key: "LEJANIAS", nombre: "Lejanías" },
    { key: "MESETAS", nombre: "Mesetas" },
    { key: "PUERTO_RICO", nombre: "Puerto Rico" },
    { key: "PUERTO_LLERAS", nombre: "Puerto Lleras" },
    { key: "URIBE", nombre: "Uribe" },
    { key: "YOPAL", nombre: "Yopal" },
    { key: "VILLANUEVA", nombre: "Villanueva" },
  ];

  const TIPOS_DOCUMENTO = [
    { value: 1, label: 'Cedula de ciudadania' },
    { value: 2, label: 'Tarjeta de identidad' },
    { value: 3, label: 'Registro civil' },
    { value: 4, label: 'Cedula de extranjeria' },
    { value: 5, label: 'Documento definido por la DIAN' },
    { value: 6, label: 'NIT' },
    { value: 7, label: 'P.E.P.' },
    { value: 8, label: 'Pasaporte' },
    { value: 9, label: 'Visa' },
  ];

  const translateErrorMessage = (message) => {
    if (message.includes('already exists')) {
      return 'Ya es asociado de Congente no puede asociarse nuevamente.';
    }
    return message;
  };

  const showNotification = (message) => {
    const translatedMessage = translateErrorMessage(message);
    setNotification({ message: translatedMessage, show: true });
    setTimeout(() => {
      setNotification({ message: '', show: false });
    }, 5000);
  };

  const showModal = (title, message) => {
    setModal({ show: true, title, message });
  };

  const handlePreRegistro = async (e) => {
    e.preventDefault();
    setLoading(true);

    if (!datosBasicos.nombres_completos || !datosBasicos.numero_cedula || 
        !datosBasicos.fecha_expedicion || !datosBasicos.agencia || !datosBasicos.tipo_documento) {
      showNotification('Por favor completa todos los campos obligatorios');
      setLoading(false);
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/preregistro/iniciar/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(datosBasicos)
      });

      if (!response.ok) {
        const errorData = await response.json();
        if (errorData?.error?.includes('ya es asociado')) {
          showModal(
            'Asociado existente',
            'Tu documento ya esta registrado como asociado. Si necesitas ayuda, contacta a un asesor.'
          );
          return;
        }
        throw new Error(errorData.detalles?.numero_cedula?.[0] || errorData.error || 'Error al crear pre-registro');
      }

      const data = await response.json();
      setPreregistroId(data.id);
      setLinkBiometria(data.link_biometria || data.url_biometria || '');
      
      if (data.link_biometria || data.url_biometria || LINK_BIOMETRIA) {
        const url = data.link_biometria || data.url_biometria || LINK_BIOMETRIA;
        window.open(url, '_blank');
      }
      
      setPaso(2);
      iniciarPollingBiometria(data.id);
      
    } catch (err) {
      showNotification(err.message);
    } finally {
      setLoading(false);
    }
  };

  const iniciarPollingBiometria = (id) => {
    consultarEstadoBiometria(id);
    
    const intervalo = setInterval(async () => {
      const estado = await consultarEstadoBiometria(id);
      
      if (estado === 'APROBADO') {
        clearInterval(intervalo);
        console.log('Biometría APROBADA - Avanzando al paso 3');
        await obtenerLinkLinix(id);
      } else if (estado === 'RECHAZADO') {
        clearInterval(intervalo);
      }
    }, 5000);
    
    return () => clearInterval(intervalo);
  };

  const consultarEstadoBiometria = async (id) => {
    try {
      const response = await fetch(`${API_BASE_URL}/preregistro/${id}/estado-biometria/`);
      
      if (!response.ok) {
        console.error('Error al consultar estado');
        return estadoBiometria;
      }
      
      const data = await response.json();
      console.log('Estado biometría:', data.estado_biometria);
      
      setEstadoBiometria(data.estado_biometria);
      
      return data.estado_biometria;
    } catch (err) {
      console.error('Error en polling:', err);
      return estadoBiometria;
    }
  };

  const obtenerLinkLinix = async (id) => {
    try {
      const response = await fetch(`${API_BASE_URL}/preregistro/${id}/link-linix/`);
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Error al obtener link de LINIX');
      }
      
      const data = await response.json();
      console.log('Link LINIX obtenido:', data.link_linix);
      
      setLinkLinix(data.link_linix);
      setPaso(3);
      
      window.open(data.link_linix, '_blank');
      
    } catch (err) {
      showNotification(err.message);
    }
  };

  const irALinix = () => {
    if (linkLinix) {
      window.open(linkLinix, '_blank');
    }
  };

  const verificarCreacionLinix = async () => {
    setLoading(true);
    
    try {
      const response = await fetch(`${API_BASE_URL}/preregistro/${preregistroId}/verificar-linix/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      const data = await response.json();
      
      if (data.completado) {
        console.log('Vinculación completada exitosamente');
        setVerificacionFinalizada(true);
        setPaso(4);
      } else {
        showNotification(data.mensaje || 'Aún no se ha completado el registro en LINIX');
      }
      
    } catch (err) {
      showNotification('Error al verificar. Por favor intenta nuevamente.');
    } finally {
      setLoading(false);
    }
  };

  const redesSociales = [
    { 
      nombre: 'WhatsApp', 
      icono: whatsappIcon,
      url: 'https://wa.me/573138875622',
    },
    { 
      nombre: 'Facebook', 
      icono: facebookIcon,
      url: 'https://facebook.com/congente',
    },
    { 
      nombre: 'TikTok', 
      icono: tiktokIcon,
      url: 'https://tiktok.com/@congente',
    },
    { 
      nombre: 'YouTube', 
      icono: youtubeIcon,
      url: 'https://youtube.com/@congente',
    },
  ];
  const actualizarDatosBasicos = (campo, valor) => {
    setDatosBasicos(prev => ({
      ...prev,
      [campo]: valor
    }));
  };

  const Notification = ({ message, show, onClose }) => {
    if (!show) return null;

    return (
      <div className="fixed top-5 right-5 bg-red-500 text-white p-4 rounded-lg shadow-lg flex items-center animate-fade-in-down">
        <AlertCircle className="w-6 h-6 mr-3" />
        <span>{message}</span>
        <button onClick={onClose} className="ml-4 text-white">
          <X className="w-5 h-5" />
        </button>
      </div>
    );
  };

  const Modal = ({ show, title, message, onClose }) => {
    if (!show) return null;

    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6 relative">
          <button onClick={onClose} className="absolute top-3 right-3 text-gray-500">
            <X className="w-5 h-5" />
          </button>
          <h3 className="text-xl font-bold mb-3" style={{ color: '#0d4974ff' }}>
            {title}
          </h3>
          <p className="text-gray-700 mb-6">{message}</p>
          <button
            onClick={onClose}
            className="w-full text-white py-2 rounded-lg font-semibold"
            style={{ backgroundColor: '#D56911' }}
          >
            Entendido
          </button>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-50 to-blue-50 py-8 px-4 sm:px-6 lg:px-8">
      <Notification 
        message={notification.message} 
        show={notification.show} 
        onClose={() => setNotification({ ...notification, show: false })} 
      />
      <Modal
        show={modal.show}
        title={modal.title}
        message={modal.message}
        onClose={() => setModal({ show: false, title: '', message: '' })}
      />
      <div className="max-w-4xl mx-auto">

        
        <div className="mb-8 flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
          <div className="text-center md:text-left">
            <div className="flex justify-center md:justify-start mb-8">
              <img src={logo} alt="Logo Congente" className="h-24" />
            </div>
            <h1 className="mt-3 text-4xl font-bold" style={{ color: '#0d4974ff' }}>
              Vinculación Digital
            </h1>
          </div>

          <div className="w-full md:w-[420px] md:ml-auto">
            <div className="flex justify-between items-center">
              {[
                { num: 1, titulo: 'Datos Básicos', icono: UserCheck },
                { num: 2, titulo: 'Validación', icono: CheckCircle },
                { num: 3, titulo: 'Formulario', icono: ExternalLink },
                { num: 4, titulo: 'Verificación', icono: Building2 }
              ].map(({ num, titulo, icono: Icon }) => (
                <div key={num} className="flex flex-col items-center flex-1">
                  <div 
                    className={`w-12 h-12 rounded-full flex items-center justify-center transition-all duration-300 ${
                      paso >= num 
                        ? 'text-white shadow-lg' 
                        : 'bg-gray-300 text-gray-600'
                    }`}
                    style={paso >= num ? { backgroundColor: '#0d4974ff' } : {}}
                  >
                    <Icon className="w-6 h-6" />
                  </div>
                  <span className={`mt-2 text-xs font-medium ${
                    paso >= num ? 'text-gray-700' : 'text-gray-500'
                  }`}>
                    {titulo}
                  </span>
                </div>
              ))}
            </div>
            <div className="relative mt-4">
              <div className="h-2 bg-gray-300 rounded-full">
                <div 
                  className="h-2 rounded-full transition-all duration-500"
                  style={{ 
                    width: `${((paso - 1) / 3) * 100}%`,
                    backgroundColor: '#D56911'
                  }}
                />
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-xl p-8">

          
          {paso === 1 && (
            <div>
              <h2 className="text-2xl font-bold text-gray-900 mb-6" style={{ color: '#0d4974ff' }}>
                Paso 1: Información Básica
              </h2>
              
              <div className="grid grid-cols-1 md:grid-cols-2 md:gap-x-8">
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Nombres Completos *
                    </label>
                    <input
                      type="text"
                      required
                      value={datosBasicos.nombres_completos}
                      onChange={(e) => actualizarDatosBasicos('nombres_completos', e.target.value)}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:border-transparent"
                      placeholder="Ej: Carlos Daniel Ortiz Angel"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Número de Cédula *
                    </label>
                    <input
                      type="text"
                      required
                      value={datosBasicos.numero_cedula}
                      onChange={(e) => actualizarDatosBasicos('numero_cedula', e.target.value)}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:border-transparent"
                      placeholder="Ej: 123456789"
                    />
                  </div>
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Fecha de Expedición *
                    </label>
                    <input
                      type="date"
                      required
                      value={datosBasicos.fecha_expedicion}
                      onChange={(e) => actualizarDatosBasicos('fecha_expedicion', e.target.value)}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:border-transparent"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Tipo de Documento *
                    </label>
                    <select
                      required
                      value={datosBasicos.tipo_documento}
                      onChange={(e) => actualizarDatosBasicos('tipo_documento', Number(e.target.value))}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:border-transparent"
                    >
                      <option value="">-- Selecciona un tipo --</option>
                      {TIPOS_DOCUMENTO.map((tipo) => (
                        <option key={tipo.value} value={tipo.value}>
                          {tipo.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>

              <div className="mt-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  ¿En qué agencia te gustaría inscribirte? *
                </label>
                <select
                  required
                  value={datosBasicos.agencia}
                  onChange={(e) => actualizarDatosBasicos('agencia', e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:border-transparent"
                >
                  <option value="">-- Selecciona una agencia --</option>
                  {AGENCIAS_DISPONIBLES.map(agencia => (
                    <option key={agencia.key} value={agencia.key}>
                      {agencia.nombre}
                    </option>
                  ))}
                </select>
              </div>

              <button
                onClick={handlePreRegistro}
                disabled={loading}
                className="mt-6 w-full text-white py-3 rounded-lg font-semibold transition-colors disabled:bg-gray-400 flex items-center justify-center"
                style={{ backgroundColor: loading ? '#9CA3AF' : '#D56911' }}
              >
                {loading ? (
                  <>
                    <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                    Procesando...
                  </>
                ) : (
                  'Continuar a Validación Biométrica'
                )}
              </button>
            </div>
          )}

{paso === 2 && (
            <div className="text-center py-12">
              <h2 className="text-2xl font-bold text-gray-900 mb-4" style={{ color: '#0d4974ff' }}>
                Validación de Identidad
              </h2>
              
              {estadoBiometria === 'APROBADO' ? (
                <>
                  <CheckCircle className="w-16 h-16 mx-auto mb-4" style={{ color: '#10B981' }} />
                  <p className="text-green-600 font-semibold mb-2">
                    ¡Validación Exitosa!
                  </p>
                  <p className="text-gray-600">
                    Redirigiendo al formulario de LINIX...
                  </p>
                </>
              ) : estadoBiometria === 'RECHAZADO' ? (
                <>
                  <AlertCircle className="w-16 h-16 text-red-600 mx-auto mb-4" />
                  <p className="text-red-600 font-semibold mb-2">
                    Validación Rechazada
                  </p>
                  <p className="text-gray-600">
                    No fue posible validar tu identidad. Por favor contacta a un asesor.
                  </p>
                </>
              ) : (
                <>
                  <Loader2 className="w-16 h-16 mx-auto mb-4 animate-spin" style={{ color: '#0d4974ff' }} />
                  <p className="text-gray-600 mb-4">
                    Esperando validación biométrica...
                  </p>
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 max-w-md mx-auto">
                    <p className="text-sm text-gray-700 mb-4">
                      {(LINK_BIOMETRIA || linkBiometria) 
                        ? 'Si aún no has completado la validación, haz clic en el botón:'
                        : 'En producción, se abrirá una ventana para validar tu identidad.'
                      }
                    </p>
                    {(LINK_BIOMETRIA || linkBiometria) && (
                      <button
                        onClick={() => window.open(linkBiometria || LINK_BIOMETRIA, '_blank')}
                        className="text-white px-6 py-2 rounded-lg transition-colors"
                        style={{ backgroundColor: '#0d4974ff' }}
                      >
                        Abrir Validación
                      </button>
                    )}
                    <p className="text-xs text-gray-500 mt-4">
                      Esta página se actualizará automáticamente cuando completes la validación.
                    </p>
                  </div>
                </>
              )}
            </div>
          )}

          {paso === 3 && (
            <div className="text-center py-12">
              <h2 className="text-2xl font-bold text-gray-900 mb-4" style={{ color: '#0d4974ff' }}>
                Completar Formulario en LINIX
              </h2>
              
              <ExternalLink className="w-16 h-16 mx-auto mb-4" style={{ color: '#0d4974ff' }} />
              
              <p className="text-gray-600 mb-6">
                Ahora debes completar el formulario de vinculación en nuestro sistema LINIX.
              </p>
              
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 max-w-md mx-auto mb-6">
                <p className="text-sm text-gray-700 mb-4">
                  Se abrió una nueva ventana con el formulario. Si no se abrió automáticamente, 
                  haz clic en el botón de abajo.
                </p>
                <button
                  onClick={irALinix}
                  className="text-white px-6 py-2 rounded-lg transition-colors mb-4"
                  style={{ backgroundColor: '#D56911' }}
                >
                  Abrir Formulario
                </button>
                <p className="text-xs text-gray-500">
                  Una vez completes el formulario, regresa a esta página y haz clic en "Verificar".
                </p>
              </div>

              <button
                onClick={verificarCreacionLinix}
                disabled={loading}
                className="text-white px-8 py-3 rounded-lg font-semibold transition-colors disabled:bg-gray-400"
                style={{ backgroundColor: loading ? '#9CA3AF' : '#0d4974ff' }}
              >
                {loading ? (
                  <>
                    <Loader2 className="w-5 h-5 inline mr-2 animate-spin" />
                    Verificando...
                  </>
                ) : (
                  'Verificar Registro'
                )}
              </button>
            </div>
          )}

          {paso === 4 && verificacionFinalizada && (
            <div className="text-center py-12">
              <CheckCircle className="w-20 h-20 mx-auto mb-4" style={{ color: '#10B981' }} />
              
              <h2 className="text-3xl font-bold text-gray-900 mb-4" style={{ color: '#0d4974ff' }}>
                ¡Vinculación Completada!
              </h2>
              
              <p className="text-lg text-gray-600 mb-6">
                Tu proceso de vinculación se completó exitosamente.
              </p>
              
              <div className="bg-green-50 border border-green-200 rounded-lg p-6 max-w-md mx-auto">
                <p className="text-sm text-gray-700">
                  Un asesor de la agencia <strong>{datosBasicos.agencia}</strong> se 
                  contactará contigo pronto para finalizar el proceso.
                </p>
              </div>

              <div className="mt-8 text-sm text-gray-600">
                <p>Número de identificación: <strong>{datosBasicos.numero_cedula}</strong></p>
                <p>Nombre: <strong>{datosBasicos.nombres_completos}</strong></p>
              </div>
            </div>
          )}
        </div>

        <div className="mt-8 text-center text-sm text-gray-600">
          <p>¡Síguenos en nuestras redes sociales!</p>
          <div className="flex justify-center space-x-4 my-4">
            {redesSociales.map(red => (
              <a key={red.nombre} href={red.url} target="_blank" rel="noopener noreferrer">
                <img src={red.icono} alt={red.nombre} className="w-6 h-6" />
              </a>
            ))}
          </div>
          <p>¿Necesitas ayuda? Contacta a nuestro equipo de soporte</p>
          <p className="mt-2">
            <a href="https://www.congente.coop" target="_blank" rel="noopener noreferrer" className="hover:underline" style={{ color: '#0d4974ff' }}>
              www.congente.coop
            </a>
          </p>
          <p className="mt-4 text-xs text-gray-500">
            &copy; 2025 Congente. Todos los derechos reservados.
          </p>
        </div>
      </div>
    </div>
  );
};

export default VinculacionDigital;
