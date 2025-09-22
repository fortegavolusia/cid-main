# Prueba del Dashboard HR con Botón de Saldo Bancario

## Pasos para probar:

1. **Acceder al dashboard de HR:**
   - URL: http://localhost:8005/dashboard
   - Necesitas estar autenticado con tu usuario (FOrtega@volusia.gov)

2. **Hacer clic en el nuevo botón "Consultar Saldo en Banco"**
   - El botón está en color verde
   - Aparece junto a los otros botones de prueba

3. **Lo que sucede internamente:**

   a) **HR System recibe la petición** del navegador con tu JWT token

   b) **HR solicita un token de servicio A2A a CIDS:**
      - Usa su API Key: `cids_ak_WoQFlNG8ckBg6ve9NuvB12XeABLs30qV`
      - Solicita permisos para Bank System
      - CIDS genera un JWT temporal (5 minutos)

   c) **HR llama a Bank System** con el token A2A:
      - Endpoint: `/accounts/by-email/FOrtega@volusia.gov/balance`
      - Bank valida el token con CIDS
      - Bank busca la cuenta por email

   d) **Bank retorna la información:**
      - Employee ID: EMP003
      - Saldo: $950,000.00
      - Nombre: Fernando Ortega

   e) **HR muestra el resultado** en el dashboard

## Resultado esperado:

```
✅ Conexión A2A exitosa con Bank System!

Información de la cuenta:
- Empleado ID: EMP003
- Email: FOrtega@volusia.gov
- Nombre: Fernando Ortega
- Saldo: $950,000.00
- Tipo de cuenta: checking
- Última actualización: [fecha/hora actual]

Este dato fue obtenido mediante comunicación A2A (Application-to-Application) con Bank System usando un JWT token temporal.
```

## Flujo A2A completo:

```
Usuario (FOrtega) → HR Dashboard → HR Backend → CIDS (token A2A) → Bank System → Respuesta
```

Todo esto sucede sin compartir API keys entre sistemas, usando tokens temporales seguros.