/**
 * Avista Privacy Guard
 * Módulo de anonimización y seudonimización antes de procesamiento por IA
 * Cumple con directrices éticas de Fundación Integra y normativa de protección de datos.
 */

// Regex para RUT chileno con o sin puntos y guión
const RUT_REGEX = /\b(\d{1,2}\.?\d{3}\.?\d{3}-?[\dkK])\b/g;

// Regex para teléfonos chilenos comunes (+569, 9xxxxxxxx, etc.)
const PHONE_REGEX = /(\+?56\s?9\s?\d{4}\s?\d{4}|9\s?\d{4}\s?\d{4}|\b[2-9]\d{7}\b)/g;

// Regex para direcciones comunes (calle, pasaje, avenida, depto)
const ADDRESS_REGEX = /\b(calle|pasaje|av\.|avenida|depto|departamento|villa|población|block)\s+[a-zA-Z0-9\s]{3,25}(?=[,.\n]|$)/gi;

// Diccionario de nombres y apellidos detectables para reemplazo seudonimizado
const COMMON_NAMES = [
  'Juan', 'Pedro', 'Lucas', 'Martina', 'Agustina', 'Sofía', 'Benjamín', 'Mateo', 
  'Emilia', 'Tomás', 'Joaquín', 'Vicente', 'Ignacia', 'Catalina', 'Francisca',
  'González', 'Muñoz', 'Rojas', 'Díaz', 'Pérez', 'Soto', 'Contreras', 'Silva'
];

export interface SanitizationResult {
  originalText: string;
  sanitizedText: string;
  detectedEntities: {
    type: 'RUT' | 'TELEFONO' | 'DIRECCION' | 'NOMBRE_PERSONAL';
    match: string;
    replacement: string;
  }[];
  wasSanitized: boolean;
}

export function sanitizePedagogicalNote(text: string, fallbackChildId: string = 'NI-PÁRVULO'): SanitizationResult {
  const detected: SanitizationResult['detectedEntities'] = [];
  let result = text;

  // 1. Sanitizar RUTs
  result = result.replace(RUT_REGEX, (match) => {
    detected.push({
      type: 'RUT',
      match,
      replacement: '[RUT_BLOQUEADO]'
    });
    return '[RUT_BLOQUEADO]';
  });

  // 2. Sanitizar Teléfonos
  result = result.replace(PHONE_REGEX, (match) => {
    detected.push({
      type: 'TELEFONO',
      match,
      replacement: '[TEL_PROTEGIDO]'
    });
    return '[TEL_PROTEGIDO]';
  });

  // 3. Sanitizar Direcciones
  result = result.replace(ADDRESS_REGEX, (match) => {
    detected.push({
      type: 'DIRECCION',
      match,
      replacement: '[DIRECCIÓN_OFUSCADA]'
    });
    return '[DIRECCIÓN_OFUSCADA]';
  });

  // 4. Seudonimizar nombres propios si aparecen explícitos
  COMMON_NAMES.forEach((name) => {
    const nameRegex = new RegExp(`\\b${name}\\b`, 'gi');
    if (nameRegex.test(result)) {
      result = result.replace(nameRegex, (match) => {
        detected.push({
          type: 'NOMBRE_PERSONAL',
          match,
          replacement: `[${fallbackChildId}]`
        });
        return `[${fallbackChildId}]`;
      });
    }
  });

  return {
    originalText: text,
    sanitizedText: result,
    detectedEntities: detected,
    wasSanitized: detected.length > 0
  };
}
