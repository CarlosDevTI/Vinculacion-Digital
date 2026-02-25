import React, { useEffect, useMemo, useState } from 'react';
import { CheckCircle, AlertCircle, Loader2, UserCheck, ExternalLink, Building2, X } from 'lucide-react';
import logo from '../assets/LogoHD.png';
import whatsappIcon from '../assets/whatsapp.svg';
import facebookIcon from '../assets/facebook.svg';
import tiktokIcon from '../assets/tiktok.svg';
import youtubeIcon from '../assets/youtube.svg';
import departmentsCatalog from '../data/departments.json';
import citiesCatalog from '../data/cities.json';
import ciiuCatalog from '../data/ciiu.json';

const parseNombreCompleto = (nombreCompleto) => {
  const partes = String(nombreCompleto || '')
    .trim()
    .toUpperCase()
    .split(/\s+/)
    .filter(Boolean);

  if (partes.length === 0) {
    return { primerNombre: '', segundoNombre: '', primerApellido: '', segundoApellido: '' };
  }
  if (partes.length === 1) {
    return { primerNombre: partes[0], segundoNombre: '', primerApellido: '', segundoApellido: '' };
  }
  if (partes.length === 2) {
    return { primerNombre: partes[0], segundoNombre: '', primerApellido: partes[1], segundoApellido: '' };
  }
  if (partes.length === 3) {
    return { primerNombre: partes[0], segundoNombre: '', primerApellido: partes[1], segundoApellido: partes[2] };
  }
  return {
    primerNombre: partes[0],
    segundoNombre: partes[1],
    primerApellido: partes[2],
    segundoApellido: partes.slice(3).join(' '),
  };
};

const COP_FORMATTER = new Intl.NumberFormat('es-CO');
const EMAIL_WITH_DOMAIN_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

const CiiuAutocompleteField = ({
  id,
  label,
  value,
  onSelect,
  options,
  placeholder,
  className = '',
}) => {
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);

  const selectedOption = useMemo(
    () => options.find((option) => option.code === String(value || '')),
    [options, value],
  );

  useEffect(() => {
    if (selectedOption) {
      setQuery(`${selectedOption.code} - ${selectedOption.description}`);
      return;
    }
    if (!open) {
      setQuery('');
    }
  }, [selectedOption, open]);

  const filteredOptions = useMemo(() => {
    const search = String(query || '').trim().toUpperCase();
    if (!search) {
      return options;
    }
    return options.filter((option) => option.searchText.includes(search));
  }, [options, query]);

  const handleSelect = (option) => {
    onSelect(option.code);
    setQuery(`${option.code} - ${option.description}`);
    setOpen(false);
  };

  const handleChange = (event) => {
    const next = String(event.target.value || '').toUpperCase();
    setQuery(next);
    onSelect('');
    setOpen(true);
  };

  const handleBlur = () => {
    setTimeout(() => setOpen(false), 120);
  };

  return (
    <div className={`relative ${className}`}>
      <label htmlFor={id} className="block text-sm font-medium text-gray-700 mb-1">
        {label}
      </label>
      <input
        id={id}
        type="text"
        value={query}
        onChange={handleChange}
        onFocus={() => setOpen(true)}
        onBlur={handleBlur}
        placeholder={placeholder}
        className="w-full px-3 py-2 border border-gray-300 rounded-lg"
        autoComplete="off"
      />

      {open && (
        <div className="absolute z-40 mt-1 w-full max-h-64 overflow-y-auto rounded-lg border border-gray-200 bg-white shadow-lg">
          {filteredOptions.length > 0 ? (
            filteredOptions.map((option) => (
              <button
                key={`${id}-${option.code}`}
                type="button"
                className="w-full px-3 py-2 text-left text-sm hover:bg-gray-100"
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => handleSelect(option)}
              >
                <span className="font-semibold">{option.code}</span>
                <span className="text-gray-600"> - {option.description}</span>
              </button>
            ))
          ) : (
            <div className="px-3 py-2 text-sm text-gray-500">
              Sin resultados. Intenta con otra palabra.
            </div>
          )}
        </div>
      )}
    </div>
  );
};

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
  const [notification, setNotification] = useState({ message: '', show: false, type: 'error' });
  const [modal, setModal] = useState({ show: false, title: '', message: '' });
  const [linkBiometria, setLinkBiometria] = useState('');
  const [verificacionFinalizada, setVerificacionFinalizada] = useState(false);
  const [vincAgilEnviada, setVincAgilEnviada] = useState(false);
  const [vincAgilLoading, setVincAgilLoading] = useState(false);
  const [ultimoEnvioLinix, setUltimoEnvioLinix] = useState(null);
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
    actividadCIIUSecundaria: '000',
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
  const [departamentoDane, setDepartamentoDane] = useState('');

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
    { key: "PUERTO_GAITAN", nombre: "Puerto Gaitan" },
    { key: "CABUYARO", nombre: "Cabuyaro" },
    { key: "VISTAHERMOSA", nombre: "Vistahermosa" },
    { key: "PUERTO_LOPEZ", nombre: "Puerto Lopez" },
    { key: "EL_CASTILLO", nombre: "El Castillo" },
    { key: "CUMARAL", nombre: "Cumaral" },
    { key: "LEJANIAS", nombre: "Lejanias" },
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

  const OCUPACION_OPTIONS = [
    { value: '1', label: 'Empleado' },
    { value: '2', label: 'Independiente' },
    { value: '3', label: 'Comerciante' },
    { value: '4', label: 'Pensionado' },
    { value: '5', label: 'Estudiante' },
    { value: '6', label: 'Ama de casa' },
    { value: '7', label: 'Desempleado' },
    { value: '8', label: 'Otro' },
  ];

  const departamentosDane = useMemo(() => {
    const data = departmentsCatalog?.data || [];
    return [...data].sort((a, b) => a.name.localeCompare(b.name));
  }, []);

  const ciudadesPorDepartamento = useMemo(() => {
    if (!departamentoDane) return [];
    const depId = Number(departamentoDane);
    const data = (citiesCatalog?.data || []).filter((c) => Number(c.departmentId) === depId);
    return data.sort((a, b) => a.name.localeCompare(b.name));
  }, [departamentoDane]);

  const ciiuOptions = useMemo(() => {
    return (ciiuCatalog || []).map((item) => {
      const code = String(item.code || '').trim();
      const description = String(item.description || '').trim();
      return {
        code,
        description,
        searchText: `${code} ${description}`.toUpperCase(),
      };
    });
  }, []);

  const translateErrorMessage = (message) => {
    if (message.includes('already exists')) {
      return 'Ya es asociado de Congente no puede asociarse nuevamente.';
    }
    return message;
  };

  const showNotification = (message, type = 'error') => {
    const translatedMessage = translateErrorMessage(message);
    setNotification({ message: translatedMessage, show: true, type });
    setTimeout(() => {
      setNotification({ message: '', show: false, type: 'error' });
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
            'Validacion bloqueada',
            'Este documento quedo vetado tras dos intentos fallidos. Por favor comunicate con Congente para habilitar un nuevo intento.'
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
        console.log('Biometria APROBADA - Avanzando al paso 3');
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
      console.log('Estado biometria:', data.estado_biometria);
      
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
      
      setVincAgilEnviada(false);
      setPaso(3);
      
    } catch (err) {
      showNotification(err.message);
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
        console.log('Vinculacion completada exitosamente');
        setVerificacionFinalizada(true);
        setPaso(4);
      } else {
        showNotification(data.mensaje || 'Aun no se ha completado el registro en LINIX');
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
    const parsed = parseNombreCompleto(datosBasicos.nombres_completos);

    setVinculacionAgil((prev) => ({
      ...prev,
      tipoDocumento: TIPO_DOCUMENTO_CORE_MAP[Number(datosBasicos.tipo_documento)] || prev.tipoDocumento,
      identificacion: datosBasicos.numero_cedula || prev.identificacion,
      primerNombre: parsed.primerNombre || prev.primerNombre,
      segundoNombre: parsed.segundoNombre || prev.segundoNombre,
      primerApellido: parsed.primerApellido || prev.primerApellido,
      segundoApellido: parsed.segundoApellido || prev.segundoApellido,
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
    const normalizadoBase = upperFields.includes(campo) ? String(valor).toUpperCase() : valor;
    const normalizado = campo === 'salario'
      ? String(normalizadoBase || '').replace(/\D/g, '')
      : normalizadoBase;
    setVinculacionAgil((prev) => {
      const siguiente = { ...prev, [campo]: normalizado };
      if (campo === 'celular') {
        siguiente.telefono = String(normalizado || '');
      }
      return siguiente;
    });
  };

  const enviarVinculacionAgil = async (e) => {
    e.preventDefault();
    if (!preregistroId) {
      showNotification('No existe pre-registro activo para enviar vinculacion agil.');
      return;
    }
    if (!departamentoDane || !vinculacionAgil.ciudad) {
      showNotification('Debes seleccionar departamento y ciudad DANE.');
      return;
    }
    if (!EMAIL_WITH_DOMAIN_REGEX.test(String(vinculacionAgil.email || '').trim().toLowerCase())) {
      showNotification('Ingresa un correo electronico valido con dominio, por ejemplo: nombre@dominio.com');
      return;
    }
    if (!vinculacionAgil.actividadCIIU) {
      showNotification('Debes seleccionar la actividad CIIU principal desde la lista.');
      return;
    }

    setVincAgilLoading(true);
    setUltimoEnvioLinix(null);
    try {
      const fechaActual = new Date().toISOString().slice(0, 10);
      const body = {
        preregistroId,
        ...vinculacionAgil,
        telefono: vinculacionAgil.celular || vinculacionAgil.telefono,
        actividadCIIUSecundaria: vinculacionAgil.actividadCIIUSecundaria || '000',
        tipoVivienda: vinculacionAgil.tipoVivienda || 'P',
        nivelEstudio: vinculacionAgil.nivelEstudio || 'U',
        actividadEconomica: vinculacionAgil.actividadEconomica || 'EM',
        operacionesMonedaExtranjera: 'N',
        declaraRenta: 'N',
        administraRecursosPublicos: 'N',
        vinculadoRecursosPublicos: 'N',
        publicamenteExpuesto: 'N',
        sucursal: vinculacionAgil.sucursal || datosBasicos.agencia || 'PRINCIPAL',
        fechaAfiliacion: vinculacionAgil.fechaAfiliacion || fechaActual,
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

      const respuestaLinix = data.respuesta_linix || {};
      const rawRespuesta = JSON.stringify(respuestaLinix);
      const esDryRun = /LINIX_DRY_RUN|modo local|simulada/i.test(rawRespuesta);
      setUltimoEnvioLinix({
        dryRun: esDryRun,
        message: respuestaLinix.message || data.mensaje || '',
        radicado: respuestaLinix.radicado || '',
      });

      setVincAgilEnviada(true);
      if (esDryRun) {
        showNotification('Vinculacion agil simulada (DRY_RUN). Ahora desactiva DRY_RUN para validar contra API real.', 'info');
      } else {
        showNotification('Vinculacion agil enviada a LINIX correctamente. Ya puedes verificar el estado final.', 'success');
      }
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

  const Notification = ({ message, show, type, onClose }) => {
    if (!show) return null;
    const isSuccess = type === 'success';
    const isInfo = type === 'info';
    const containerClass = isSuccess
      ? 'bg-green-600'
      : isInfo
        ? 'bg-amber-500'
        : 'bg-red-500';
    const Icon = isSuccess ? CheckCircle : AlertCircle;

    return (
      <div className={`fixed top-5 right-5 text-white p-4 rounded-lg shadow-lg flex items-center animate-fade-in-down ${containerClass}`}>
        <Icon className="w-6 h-6 mr-3" />
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
        type={notification.type}
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
              Vinculacion Digital
            </h1>
          </div>

          <div className="w-full md:w-[420px] md:ml-auto">
            <div className="flex justify-between items-center">
              {[
                { num: 1, titulo: 'Datos Basicos', icono: UserCheck },
                { num: 2, titulo: 'Validacion', icono: CheckCircle },
                { num: 3, titulo: 'Formulario', icono: ExternalLink },
                { num: 4, titulo: 'Verificacion', icono: Building2 }
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
                Paso 1: Informacion Basica
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
                      Numero de Cedula *
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
                      Fecha de Expedicion *
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
                  En que agencia te gustaria inscribirte? *
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
                  'Continuar a Validacion Biometrica'
                )}
              </button>
            </div>
          )}

{paso === 2 && (
            <div className="text-center py-12">
              <h2 className="text-2xl font-bold text-gray-900 mb-4" style={{ color: '#0d4974ff' }}>
                Validacion de Identidad
              </h2>
              
              {estadoBiometria === 'APROBADO' ? (
                <>
                  <CheckCircle className="w-16 h-16 mx-auto mb-4" style={{ color: '#10B981' }} />
                  <p className="text-green-600 font-semibold mb-2">
                    Validacion Exitosa!
                  </p>
                  <p className="text-gray-600">
                    {estadoBiometriaInfo.mensaje || 'Redirigiendo al formulario de LINIX...'}
                  </p>
                </>
              ) : estadoBiometria === 'RECHAZADO' ? (
                <>
                  <AlertCircle className="w-16 h-16 text-red-600 mx-auto mb-4" />
                  <p className="text-red-600 font-semibold mb-2">
                    Validacion Rechazada
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
                    Reintentar Validacion
                  </button>
                </>
              ) : (
                <>
                  <Loader2 className="w-16 h-16 mx-auto mb-4 animate-spin" style={{ color: '#0d4974ff' }} />
                  <p className="text-gray-600 mb-4">
                    {estadoBiometriaInfo.mensaje || 'Esperando validacion biometrica...'}
                  </p>
                  {estadoBiometriaInfo.justificacion && (
                    <p className="text-sm text-gray-500 mb-4">
                      {resumenJustificacion(estadoBiometriaInfo.justificacion)}
                    </p>
                  )}
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 max-w-md mx-auto">
                    <p className="text-sm text-gray-700 mb-4">
                      {(LINK_BIOMETRIA || linkBiometria) 
                        ? 'Si aun no has completado la validacion, haz clic en el boton:'
                        : 'En produccion, se abrira una ventana para validar tu identidad.'
                      }
                    </p>
                    {(LINK_BIOMETRIA || linkBiometria) && (
                      <button
                        onClick={() => window.open(linkBiometria || LINK_BIOMETRIA, '_blank')}
                        className="text-white px-6 py-2 rounded-lg transition-colors"
                        style={{ backgroundColor: '#0d4974ff' }}
                      >
                        Abrir Validacion
                      </button>
                    )}
                    <p className="text-xs text-gray-500 mt-4">
                      Esta pagina se actualizara automaticamente cuando completes la validacion.
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
                Completa los datos requeridos para radicar la vinculacion al core LINIX.
              </p>
              <form onSubmit={enviarVinculacionAgil} className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Tipo de documento *</label>
                    <select value={vinculacionAgil.tipoDocumento} onChange={(e) => actualizarVinculacionAgil('tipoDocumento', e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg">
                      <option value="C">Cedula</option>
                      <option value="T">Tarjeta de identidad</option>
                      <option value="E">Cedula de extranjeria</option>
                      <option value="N">NIT</option>
                      <option value="P">Pasaporte</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Identificacion *</label>
                    <input className="w-full px-3 py-2 border border-gray-300 rounded-lg" value={vinculacionAgil.identificacion} onChange={(e) => actualizarVinculacionAgil('identificacion', e.target.value)} required />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Fecha de nacimiento *</label>
                    <input type="date" className="w-full px-3 py-2 border border-gray-300 rounded-lg" value={vinculacionAgil.fechaNacimiento} onChange={(e) => actualizarVinculacionAgil('fechaNacimiento', e.target.value)} required />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Primer nombre *</label>
                    <input className="w-full px-3 py-2 border border-gray-300 rounded-lg" value={vinculacionAgil.primerNombre} onChange={(e) => actualizarVinculacionAgil('primerNombre', e.target.value)} required />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Segundo nombre</label>
                    <input className="w-full px-3 py-2 border border-gray-300 rounded-lg" value={vinculacionAgil.segundoNombre} onChange={(e) => actualizarVinculacionAgil('segundoNombre', e.target.value)} />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Primer apellido *</label>
                    <input className="w-full px-3 py-2 border border-gray-300 rounded-lg" value={vinculacionAgil.primerApellido} onChange={(e) => actualizarVinculacionAgil('primerApellido', e.target.value)} required />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Segundo apellido</label>
                    <input className="w-full px-3 py-2 border border-gray-300 rounded-lg" value={vinculacionAgil.segundoApellido} onChange={(e) => actualizarVinculacionAgil('segundoApellido', e.target.value)} />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Genero *</label>
                    <select value={vinculacionAgil.genero} onChange={(e) => actualizarVinculacionAgil('genero', e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg"><option value="M">Masculino</option><option value="F">Femenino</option></select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Estado civil *</label>
                    <select value={vinculacionAgil.estadoCivil} onChange={(e) => actualizarVinculacionAgil('estadoCivil', e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg"><option value="S">Soltero</option><option value="C">Casado</option><option value="U">Union libre</option></select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Correo electronico *</label>
                    <input type="email" className="w-full px-3 py-2 border border-gray-300 rounded-lg" value={vinculacionAgil.email} onChange={(e) => actualizarVinculacionAgil('email', e.target.value)} required />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Celular *</label>
                    <input className="w-full px-3 py-2 border border-gray-300 rounded-lg" value={vinculacionAgil.celular} onChange={(e) => actualizarVinculacionAgil('celular', e.target.value)} required />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Direccion *</label>
                    <input className="w-full px-3 py-2 border border-gray-300 rounded-lg" value={vinculacionAgil.direccion} onChange={(e) => actualizarVinculacionAgil('direccion', e.target.value)} required />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Barrio *</label>
                    <input className="w-full px-3 py-2 border border-gray-300 rounded-lg" value={vinculacionAgil.barrio} onChange={(e) => actualizarVinculacionAgil('barrio', e.target.value)} required />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Departamento DANE *</label>
                    <select value={departamentoDane} onChange={(e) => { setDepartamentoDane(e.target.value); actualizarVinculacionAgil('ciudad', ''); }} className="w-full px-3 py-2 border border-gray-300 rounded-lg">
                      <option value="">Seleccione departamento</option>
                      {departamentosDane.map((dep) => (
                        <option key={dep.id} value={dep.id}>{dep.name}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Ciudad (codigo DANE) *</label>
                    <select value={vinculacionAgil.ciudad} onChange={(e) => actualizarVinculacionAgil('ciudad', e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg">
                      <option value="">Seleccione ciudad</option>
                      {ciudadesPorDepartamento.map((city) => (
                        <option key={city.id} value={String(city.id)}>
                          {city.name} - {city.id}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div><label className="block text-sm font-medium text-gray-700 mb-1">Estrato *</label><input type="number" min="1" max="6" className="w-full px-3 py-2 border border-gray-300 rounded-lg" value={vinculacionAgil.estrato} onChange={(e) => actualizarVinculacionAgil('estrato', Number(e.target.value))} required /></div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Ocupacion *</label>
                    <select className="w-full px-3 py-2 border border-gray-300 rounded-lg" value={vinculacionAgil.ocupacion} onChange={(e) => actualizarVinculacionAgil('ocupacion', e.target.value)} required>
                      {OCUPACION_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>{option.label}</option>
                      ))}
                    </select>
                  </div>
                  <CiiuAutocompleteField
                    id="actividad-ciiu-principal"
                    label="Actividad CIIU principal *"
                    value={vinculacionAgil.actividadCIIU}
                    onSelect={(code) => actualizarVinculacionAgil('actividadCIIU', code)}
                    options={ciiuOptions}
                    placeholder="Escribe codigo o actividad (ej: SISTEMAS)"
                    className="md:col-span-2"
                  />
                  <div><label className="block text-sm font-medium text-gray-700 mb-1">Personas a cargo *</label><input type="number" min="0" className="w-full px-3 py-2 border border-gray-300 rounded-lg" value={vinculacionAgil.personasCargo} onChange={(e) => actualizarVinculacionAgil('personasCargo', Number(e.target.value))} required /></div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Salario (COP) *</label>
                    <input
                      type="text"
                      inputMode="numeric"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                      value={vinculacionAgil.salario ? COP_FORMATTER.format(Number(vinculacionAgil.salario)) : ''}
                      onChange={(e) => actualizarVinculacionAgil('salario', e.target.value)}
                      placeholder="2.400.000"
                      required
                    />
                  </div>
                  <div><label className="block text-sm font-medium text-gray-700 mb-1">Poblacion vulnerable *</label><select value={vinculacionAgil.poblacionVulnerable} onChange={(e) => actualizarVinculacionAgil('poblacionVulnerable', e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg"><option value="N">No</option><option value="S">Si</option></select></div>
                </div>

                <div className="flex flex-col md:flex-row gap-3">
                  <button type="submit" disabled={vincAgilLoading} className="text-white px-6 py-2 rounded-lg transition-colors disabled:bg-gray-400" style={{ backgroundColor: vincAgilLoading ? '#9CA3AF' : '#D56911' }}>
                    {vincAgilLoading ? 'Subiendo vinculacion...' : 'Enviar Vinculacion Agil'}
                  </button>
                  <button type="button" onClick={verificarCreacionLinix} disabled={loading || !vincAgilEnviada} className="text-white px-8 py-2 rounded-lg font-semibold transition-colors disabled:bg-gray-400" style={{ backgroundColor: loading || !vincAgilEnviada ? '#9CA3AF' : '#0d4974ff' }}>
                    {loading ? 'Verificando...' : 'Verificar Registro'}
                  </button>
                </div>

                {vincAgilLoading && (
                  <div className="rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-blue-900 flex items-center gap-2">
                    <Loader2 className="w-5 h-5 animate-spin" />
                    <p className="text-sm font-medium">Subiendo vinculacion agil al core LINIX. Espera unos segundos...</p>
                  </div>
                )}

                {ultimoEnvioLinix && !vincAgilLoading && (
                  <div className={`rounded-lg px-4 py-3 flex items-start gap-2 ${
                    ultimoEnvioLinix.dryRun ? 'border border-amber-300 bg-amber-50 text-amber-900' : 'border border-green-300 bg-green-50 text-green-900'
                  }`}>
                    <CheckCircle className="w-5 h-5 mt-0.5 flex-shrink-0" />
                    <div className="text-sm">
                      <p className="font-medium">
                        {ultimoEnvioLinix.dryRun ? 'Vinculacion enviada en modo simulado (DRY_RUN).' : 'Vinculacion enviada correctamente a LINIX.'}
                      </p>
                      {ultimoEnvioLinix.radicado && (
                        <p>Radicado: <strong>{ultimoEnvioLinix.radicado}</strong></p>
                      )}
                      {ultimoEnvioLinix.message && (
                        <p>{ultimoEnvioLinix.message}</p>
                      )}
                    </div>
                  </div>
                )}

                {!vincAgilEnviada && (
                  <div className="rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-amber-900 flex items-start gap-2">
                    <AlertCircle className="w-5 h-5 mt-0.5 flex-shrink-0" />
                    <p className="text-sm font-medium">Debes enviar la vinculacion agil antes de ejecutar la verificacion final.</p>
                  </div>
                )}
              </form>
            </div>
          )}

          {paso === 4 && verificacionFinalizada && (
            <div className="text-center py-12">
              <CheckCircle className="w-20 h-20 mx-auto mb-4" style={{ color: '#10B981' }} />
              
              <h2 className="text-3xl font-bold text-gray-900 mb-4" style={{ color: '#0d4974ff' }}>
                Vinculacion Completada!
              </h2>
              
              <p className="text-lg text-gray-600 mb-6">
                Tu proceso de vinculacion se completo exitosamente.
              </p>
              
              <div className="bg-green-50 border border-green-200 rounded-lg p-6 max-w-md mx-auto">
                <p className="text-sm text-gray-700">
                  Un asesor de la agencia <strong>{datosBasicos.agencia}</strong> se 
                  contactara contigo pronto para finalizar el proceso.
                </p>
              </div>

              <div className="mt-8 text-sm text-gray-600">
                <p>Numero de identificacion: <strong>{datosBasicos.numero_cedula}</strong></p>
                <p>Nombre: <strong>{datosBasicos.nombres_completos}</strong></p>
              </div>
            </div>
          )}
        </div>

        <div className="mt-8 text-center text-sm text-gray-600">
          <p>Siguenos en nuestras redes sociales!</p>
          <div className="flex justify-center space-x-4 my-4">
            {redesSociales.map(red => (
              <a key={red.nombre} href={red.url} target="_blank" rel="noopener noreferrer">
                <img src={red.icono} alt={red.nombre} className="w-6 h-6" />
              </a>
            ))}
          </div>
          <p>Necesitas ayuda? Contacta a nuestro equipo de soporte</p>
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
