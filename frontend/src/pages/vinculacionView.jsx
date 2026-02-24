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
  const [vincAgilEnviada, setVincAgilEnviada] = useState(false);
  const [vincAgilLoading, setVincAgilLoading] = useState(false);
  const [vinculacionAgil, setVinculacionAgil] = useState({
    tipoDocumento: 'C',
    identificacion: '',
    primerNombre: '',
    segundoNombre: '',
    primerApellido: '',
    segundoApellido: '',
    fechaNacimiento: '',
    genero: 'M',
    estadoCivil: 'S',
    email: '',
    celular: '',
    telefono: '',
    direccion: '',
    barrio: '',
    ciudad: '',
    estrato: 3,
    tipoVivienda: 'P',
    nivelEstudio: 'U',
    actividadEconomica: 'EM',
    ocupacion: '1',
    actividadCIIU: '',
    actividadCIIUSecundaria: '',
    poblacionVulnerable: 'N',
    publicamenteExpuesto: 'N',
    personasCargo: 0,
    salario: '',
    operacionesMonedaExtranjera: 'N',
    declaraRenta: 'N',
    administraRecursosPublicos: 'N',
    vinculadoRecursosPublicos: 'N',
    sucursal: '102',
    fechaAfiliacion: new Date().toISOString().slice(0, 10),
  });
  const [estadoBiometriaInfo, setEstadoBiometriaInfo] = useState({
    mensaje: '',
    justificacion: ''
  });

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
    { key: "PUERTO_GAITAN", nombre: "Puerto Gait??n" },
    { key: "CABUYARO", nombre: "Cabuyaro" },
    { key: "VISTAHERMOSA", nombre: "Vistahermosa" },
    { key: "PUERTO_LOPEZ", nombre: "Puerto L??pez" },
    { key: "EL_CASTILLO", nombre: "El Castillo" },
    { key: "CUMARAL", nombre: "Cumaral" },
    { key: "LEJANIAS", nombre: "Lejan??as" },
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

  const TIPO_DOCUMENTO_CORE_MAP = {
    1: 'C',
    2: 'T',
    3: 'R',
    4: 'E',
    6: 'N',
    8: 'P',
  };

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

  const crearPreRegistro = async () => {
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
        if (response.status === 403 && errorData?.codigo === 'VETADO') {
          showModal(
            'Validaci??n bloqueada',
            'Este documento qued?? vetado tras dos intentos fallidos. Por favor comun??cate con Congente para habilitar un nuevo intento.'
          );
          return;
        }
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
      setEstadoBiometriaInfo({ mensaje: '', justificacion: '' });
      
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

  const handlePreRegistro = async (e) => {
    e.preventDefault();
    await crearPreRegistro();
  };

  const reintentarValidacion = async () => {
    await crearPreRegistro();
  };

  const iniciarPollingBiometria = (id) => {
    consultarEstadoBiometria(id);
    
    const intervalo = setInterval(async () => {
      const estado = await consultarEstadoBiometria(id);
      
      if (estado === 'APROBADO') {
        clearInterval(intervalo);
        console.log('Biometr??a APROBADA - Avanzando al paso 3');
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
      console.log('Estado biometr??a:', data.estado_biometria);
      
      setEstadoBiometria(data.estado_biometria);
      setEstadoBiometriaInfo({
        mensaje: data.mensaje || '',
        justificacion: data.justificacion || ''
      });
      
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
      setVincAgilEnviada(false);
      setPaso(3);
      
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
    if (!vincAgilEnviada) {
      showNotification('Primero debes enviar la vinculacion agil en este paso.');
      return;
    }

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
        console.log('Vinculaci??n completada exitosamente');
        setVerificacionFinalizada(true);
        setPaso(4);
      } else {
        showNotification(data.mensaje || 'A??n no se ha completado el registro en LINIX');
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
    const valorNormalizado = campo === 'nombres_completos'
      ? valor.toUpperCase()
      : valor;
    setDatosBasicos(prev => ({
      ...prev,
      [campo]: valorNormalizado
    }));
  };

  useEffect(() => {
    const nombres = (datosBasicos.nombres_completos || '').trim().split(/\s+/).filter(Boolean);
    const primerNombre = nombres[0] || '';
    const segundoNombre = nombres.length > 1 ? nombres.slice(1).join(' ') : '';

    setVinculacionAgil((prev) => ({
      ...prev,
      tipoDocumento: TIPO_DOCUMENTO_CORE_MAP[Number(datosBasicos.tipo_documento)] || prev.tipoDocumento,
      identificacion: datosBasicos.numero_cedula || prev.identificacion,
      primerNombre: prev.primerNombre || primerNombre,
      segundoNombre: prev.segundoNombre || segundoNombre,
      sucursal: datosBasicos.agencia || prev.sucursal,
    }));
  }, [datosBasicos.nombres_completos, datosBasicos.numero_cedula, datosBasicos.tipo_documento, datosBasicos.agencia]);

  const actualizarVinculacionAgil = (campo, valor) => {
    const upperFields = [
      'primerNombre',
      'segundoNombre',
      'primerApellido',
      'segundoApellido',
      'direccion',
      'barrio'
    ];
    const normalizado = upperFields.includes(campo) ? String(valor).toUpperCase() : valor;
    setVinculacionAgil((prev) => ({ ...prev, [campo]: normalizado }));
  };

  const enviarVinculacionAgil = async (e) => {
    e.preventDefault();
    if (!preregistroId) {
      showNotification('No existe pre-registro activo para enviar vinculacion agil.');
      return;
    }

    setVincAgilLoading(true);
    try {
      const body = {
        preregistroId,
        ...vinculacionAgil,
      };
      const response = await fetch(`${API_BASE_URL}/vinculacion-agil/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      const data = await response.json();
      if (!response.ok || !data.ok) {
        throw new Error(data.detalle || data.error || 'Error enviando vinculacion agil.');
      }

      setVincAgilEnviada(true);
      showNotification('Vinculacion agil enviada a LINIX. Ahora puedes verificar el estado final.');
    } catch (err) {
      showNotification(err.message);
    } finally {
      setVincAgilLoading(false);
    }
  };

  const resumenJustificacion = (texto) => {
    if (!texto) return '';
    const limpio = String(texto).trim();
    if (limpio.length <= 90) return limpio;
    return `${limpio.slice(0, 90)}...`;
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
              Vinculaci??n Digital
            </h1>
          </div>

          <div className="w-full md:w-[420px] md:ml-auto">
            <div className="flex justify-between items-center">
              {[
                { num: 1, titulo: 'Datos B??sicos', icono: UserCheck },
                { num: 2, titulo: 'Validaci??n', icono: CheckCircle },
                { num: 3, titulo: 'Formulario', icono: ExternalLink },
                { num: 4, titulo: 'Verificaci??n', icono: Building2 }
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
                Paso 1: Informaci??n B??sica
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
                      N??mero de C??dula *
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
                      Fecha de Expedici??n *
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
                  ??En qu?? agencia te gustar??a inscribirte? *
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
                  'Continuar a Validaci??n Biom??trica'
                )}
              </button>
            </div>
          )}

{paso === 2 && (
            <div className="text-center py-12">
              <h2 className="text-2xl font-bold text-gray-900 mb-4" style={{ color: '#0d4974ff' }}>
                Validaci??n de Identidad
              </h2>
              
              {estadoBiometria === 'APROBADO' ? (
                <>
                  <CheckCircle className="w-16 h-16 mx-auto mb-4" style={{ color: '#10B981' }} />
                  <p className="text-green-600 font-semibold mb-2">
                    ??Validaci??n Exitosa!
                  </p>
                  <p className="text-gray-600">
                    {estadoBiometriaInfo.mensaje || 'Redirigiendo al formulario de LINIX...'}
                  </p>
                </>
              ) : estadoBiometria === 'RECHAZADO' ? (
                <>
                  <AlertCircle className="w-16 h-16 text-red-600 mx-auto mb-4" />
                  <p className="text-red-600 font-semibold mb-2">
                    Validaci??n Rechazada
                  </p>
                  <p className="text-gray-600">
                    {estadoBiometriaInfo.mensaje || 'No fue posible validar tu identidad.'}
                  </p>
                  {estadoBiometriaInfo.justificacion && (
                    <p className="text-sm text-gray-500 mt-2">
                      Motivo: {resumenJustificacion(estadoBiometriaInfo.justificacion)}
                    </p>
                  )}
                  <button
                    onClick={reintentarValidacion}
                    disabled={loading}
                    className="mt-6 text-white px-6 py-2 rounded-lg transition-colors disabled:bg-gray-400"
                    style={{ backgroundColor: loading ? '#9CA3AF' : '#D56911' }}
                  >
                    Reintentar Validaci??n
                  </button>
                </>
              ) : (
                <>
                  <Loader2 className="w-16 h-16 mx-auto mb-4 animate-spin" style={{ color: '#0d4974ff' }} />
                  <p className="text-gray-600 mb-4">
                    {estadoBiometriaInfo.mensaje || 'Esperando validaci??n biom??trica...'}
                  </p>
                  {estadoBiometriaInfo.justificacion && (
                    <p className="text-sm text-gray-500 mb-4">
                      {resumenJustificacion(estadoBiometriaInfo.justificacion)}
                    </p>
                  )}
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 max-w-md mx-auto">
                    <p className="text-sm text-gray-700 mb-4">
                      {(LINK_BIOMETRIA || linkBiometria) 
                        ? 'Si a??n no has completado la validaci??n, haz clic en el bot??n:'
                        : 'En producci??n, se abrir?? una ventana para validar tu identidad.'
                      }
                    </p>
                    {(LINK_BIOMETRIA || linkBiometria) && (
                      <button
                        onClick={() => window.open(linkBiometria || LINK_BIOMETRIA, '_blank')}
                        className="text-white px-6 py-2 rounded-lg transition-colors"
                        style={{ backgroundColor: '#0d4974ff' }}
                      >
                        Abrir Validaci??n
                      </button>
                    )}
                    <p className="text-xs text-gray-500 mt-4">
                      Esta p??gina se actualizar?? autom??ticamente cuando completes la validaci??n.
                    </p>
                  </div>
                </>
              )}
            </div>
          )}

          {paso === 3 && (
            <div className="py-4">
              <h2 className="text-2xl font-bold text-gray-900 mb-4" style={{ color: '#0d4974ff' }}>
                Paso 3: Vinculacion Agil
              </h2>

              <p className="text-gray-600 mb-6">
                Diligencia los datos minimos para construir y enviar la trama al core LINIX.
              </p>

              <form onSubmit={enviarVinculacionAgil} className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <select value={vinculacionAgil.tipoDocumento} onChange={(e) => actualizarVinculacionAgil('tipoDocumento', e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg">
                    <option value="C">Cedula</option>
                    <option value="T">Tarjeta Identidad</option>
                    <option value="E">Cedula Extranjeria</option>
                    <option value="N">NIT</option>
                    <option value="P">Pasaporte</option>
                  </select>
                  <input className="w-full px-3 py-2 border border-gray-300 rounded-lg" placeholder="Identificacion *" value={vinculacionAgil.identificacion} onChange={(e) => actualizarVinculacionAgil('identificacion', e.target.value)} required />
                  <input type="date" className="w-full px-3 py-2 border border-gray-300 rounded-lg" value={vinculacionAgil.fechaNacimiento} onChange={(e) => actualizarVinculacionAgil('fechaNacimiento', e.target.value)} required />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <input className="w-full px-3 py-2 border border-gray-300 rounded-lg" placeholder="Primer Nombre *" value={vinculacionAgil.primerNombre} onChange={(e) => actualizarVinculacionAgil('primerNombre', e.target.value)} required />
                  <input className="w-full px-3 py-2 border border-gray-300 rounded-lg" placeholder="Segundo Nombre" value={vinculacionAgil.segundoNombre} onChange={(e) => actualizarVinculacionAgil('segundoNombre', e.target.value)} />
                  <input className="w-full px-3 py-2 border border-gray-300 rounded-lg" placeholder="Primer Apellido *" value={vinculacionAgil.primerApellido} onChange={(e) => actualizarVinculacionAgil('primerApellido', e.target.value)} required />
                  <input className="w-full px-3 py-2 border border-gray-300 rounded-lg" placeholder="Segundo Apellido" value={vinculacionAgil.segundoApellido} onChange={(e) => actualizarVinculacionAgil('segundoApellido', e.target.value)} />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <select value={vinculacionAgil.genero} onChange={(e) => actualizarVinculacionAgil('genero', e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg"><option value="M">Masculino</option><option value="F">Femenino</option></select>
                  <select value={vinculacionAgil.estadoCivil} onChange={(e) => actualizarVinculacionAgil('estadoCivil', e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg"><option value="S">Soltero</option><option value="C">Casado</option><option value="U">Union Libre</option></select>
                  <input type="email" className="w-full px-3 py-2 border border-gray-300 rounded-lg" placeholder="Email *" value={vinculacionAgil.email} onChange={(e) => actualizarVinculacionAgil('email', e.target.value)} required />
                  <input className="w-full px-3 py-2 border border-gray-300 rounded-lg" placeholder="Celular *" value={vinculacionAgil.celular} onChange={(e) => actualizarVinculacionAgil('celular', e.target.value)} required />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <input className="w-full px-3 py-2 border border-gray-300 rounded-lg" placeholder="Telefono" value={vinculacionAgil.telefono} onChange={(e) => actualizarVinculacionAgil('telefono', e.target.value)} />
                  <input className="w-full px-3 py-2 border border-gray-300 rounded-lg" placeholder="Direccion *" value={vinculacionAgil.direccion} onChange={(e) => actualizarVinculacionAgil('direccion', e.target.value)} required />
                  <input className="w-full px-3 py-2 border border-gray-300 rounded-lg" placeholder="Barrio *" value={vinculacionAgil.barrio} onChange={(e) => actualizarVinculacionAgil('barrio', e.target.value)} required />
                  <input className="w-full px-3 py-2 border border-gray-300 rounded-lg" placeholder="Ciudad DANE *" value={vinculacionAgil.ciudad} onChange={(e) => actualizarVinculacionAgil('ciudad', e.target.value)} required />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <input type="number" min="1" max="6" className="w-full px-3 py-2 border border-gray-300 rounded-lg" placeholder="Estrato *" value={vinculacionAgil.estrato} onChange={(e) => actualizarVinculacionAgil('estrato', Number(e.target.value))} required />
                  <input className="w-full px-3 py-2 border border-gray-300 rounded-lg" placeholder="Tipo Vivienda *" value={vinculacionAgil.tipoVivienda} onChange={(e) => actualizarVinculacionAgil('tipoVivienda', e.target.value)} required />
                  <input className="w-full px-3 py-2 border border-gray-300 rounded-lg" placeholder="Nivel Estudio *" value={vinculacionAgil.nivelEstudio} onChange={(e) => actualizarVinculacionAgil('nivelEstudio', e.target.value)} required />
                  <input className="w-full px-3 py-2 border border-gray-300 rounded-lg" placeholder="Actividad Economica *" value={vinculacionAgil.actividadEconomica} onChange={(e) => actualizarVinculacionAgil('actividadEconomica', e.target.value)} required />
                  <input className="w-full px-3 py-2 border border-gray-300 rounded-lg" placeholder="Ocupacion *" value={vinculacionAgil.ocupacion} onChange={(e) => actualizarVinculacionAgil('ocupacion', e.target.value)} required />
                  <input className="w-full px-3 py-2 border border-gray-300 rounded-lg" placeholder="CIIU *" value={vinculacionAgil.actividadCIIU} onChange={(e) => actualizarVinculacionAgil('actividadCIIU', e.target.value)} required />
                  <input className="w-full px-3 py-2 border border-gray-300 rounded-lg" placeholder="CIIU Secundario *" value={vinculacionAgil.actividadCIIUSecundaria} onChange={(e) => actualizarVinculacionAgil('actividadCIIUSecundaria', e.target.value)} required />
                  <input type="number" min="0" className="w-full px-3 py-2 border border-gray-300 rounded-lg" placeholder="Personas a cargo *" value={vinculacionAgil.personasCargo} onChange={(e) => actualizarVinculacionAgil('personasCargo', Number(e.target.value))} required />
                  <input type="number" min="0" className="w-full px-3 py-2 border border-gray-300 rounded-lg" placeholder="Salario *" value={vinculacionAgil.salario} onChange={(e) => actualizarVinculacionAgil('salario', e.target.value)} required />
                  <select value={vinculacionAgil.poblacionVulnerable} onChange={(e) => actualizarVinculacionAgil('poblacionVulnerable', e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg"><option value="N">Poblacion vulnerable: No</option><option value="S">Poblacion vulnerable: Si</option></select>
                  <select value={vinculacionAgil.publicamenteExpuesto} onChange={(e) => actualizarVinculacionAgil('publicamenteExpuesto', e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg"><option value="N">PEP: No</option><option value="S">PEP: Si</option></select>
                  <select value={vinculacionAgil.operacionesMonedaExtranjera} onChange={(e) => actualizarVinculacionAgil('operacionesMonedaExtranjera', e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg"><option value="N">Moneda extranjera: No</option><option value="S">Moneda extranjera: Si</option></select>
                  <select value={vinculacionAgil.declaraRenta} onChange={(e) => actualizarVinculacionAgil('declaraRenta', e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg"><option value="N">Declara renta: No</option><option value="S">Declara renta: Si</option></select>
                  <select value={vinculacionAgil.administraRecursosPublicos} onChange={(e) => actualizarVinculacionAgil('administraRecursosPublicos', e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg"><option value="N">Administra recursos publicos: No</option><option value="S">Administra recursos publicos: Si</option></select>
                  <select value={vinculacionAgil.vinculadoRecursosPublicos} onChange={(e) => actualizarVinculacionAgil('vinculadoRecursosPublicos', e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg"><option value="N">Vinculado recursos publicos: No</option><option value="S">Vinculado recursos publicos: Si</option></select>
                  <input className="w-full px-3 py-2 border border-gray-300 rounded-lg" placeholder="Sucursal *" value={vinculacionAgil.sucursal} onChange={(e) => actualizarVinculacionAgil('sucursal', e.target.value)} required />
                  <input type="date" className="w-full px-3 py-2 border border-gray-300 rounded-lg" value={vinculacionAgil.fechaAfiliacion} onChange={(e) => actualizarVinculacionAgil('fechaAfiliacion', e.target.value)} required />
                </div>

                <div className="flex flex-col md:flex-row gap-3">
                  <button type="submit" disabled={vincAgilLoading} className="text-white px-6 py-2 rounded-lg transition-colors disabled:bg-gray-400" style={{ backgroundColor: vincAgilLoading ? '#9CA3AF' : '#D56911' }}>
                    {vincAgilLoading ? 'Enviando...' : 'Enviar Vinculacion Agil'}
                  </button>
                  <button type="button" onClick={irALinix} className="text-white px-6 py-2 rounded-lg transition-colors" style={{ backgroundColor: '#0d4974ff' }}>
                    Abrir LINIX Externo (Opcional)
                  </button>
                  <button type="button" onClick={verificarCreacionLinix} disabled={loading || !vincAgilEnviada} className="text-white px-8 py-2 rounded-lg font-semibold transition-colors disabled:bg-gray-400" style={{ backgroundColor: loading || !vincAgilEnviada ? '#9CA3AF' : '#0d4974ff' }}>
                    {loading ? 'Verificando...' : 'Verificar Registro'}
                  </button>
                </div>
                {!vincAgilEnviada && (
                  <p className="text-sm text-gray-500">Debes enviar la vinculacion agil antes de ejecutar la verificacion final.</p>
                )}
              </form>
            </div>
          )}

          {paso === 4 && verificacionFinalizada && (
            <div className="text-center py-12">
              <CheckCircle className="w-20 h-20 mx-auto mb-4" style={{ color: '#10B981' }} />
              
              <h2 className="text-3xl font-bold text-gray-900 mb-4" style={{ color: '#0d4974ff' }}>
                ??Vinculaci??n Completada!
              </h2>
              
              <p className="text-lg text-gray-600 mb-6">
                Tu proceso de vinculaci??n se complet?? exitosamente.
              </p>
              
              <div className="bg-green-50 border border-green-200 rounded-lg p-6 max-w-md mx-auto">
                <p className="text-sm text-gray-700">
                  Un asesor de la agencia <strong>{datosBasicos.agencia}</strong> se 
                  contactar?? contigo pronto para finalizar el proceso.
                </p>
              </div>

              <div className="mt-8 text-sm text-gray-600">
                <p>N??mero de identificaci??n: <strong>{datosBasicos.numero_cedula}</strong></p>
                <p>Nombre: <strong>{datosBasicos.nombres_completos}</strong></p>
              </div>
            </div>
          )}
        </div>

        <div className="mt-8 text-center text-sm text-gray-600">
          <p>??S??guenos en nuestras redes sociales!</p>
          <div className="flex justify-center space-x-4 my-4">
            {redesSociales.map(red => (
              <a key={red.nombre} href={red.url} target="_blank" rel="noopener noreferrer">
                <img src={red.icono} alt={red.nombre} className="w-6 h-6" />
              </a>
            ))}
          </div>
          <p>??Necesitas ayuda? Contacta a nuestro equipo de soporte</p>
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

