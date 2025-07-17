# 🤖 AGV Fleet Commander

## Sistema Inteligente de Gestión de Flota AGV
**Puerto de Chancay • Arquitectura Hexagonal + IA**

---

## 🎯 Descripción del Proyecto

**AGV Fleet Commander** es un sistema de gestión inteligente para flotas de vehículos guiados automatizados (AGV) diseñado específicamente para las operaciones del Puerto de Chancay. El sistema implementa **Arquitectura Hexagonal** (Ports & Adapters) integrada con **OpenAI GPT-4o mini** para optimización inteligente de rutas, asignación de tareas y análisis predictivo.

### 🏗️ Características Principales

- **🤖 Optimización IA**: Rutas inteligentes y asignación de tareas con OpenAI GPT-4o mini
- **📊 Monitoreo en Tiempo Real**: Dashboard interactivo con métricas de flota
- **🔧 Arquitectura Hexagonal**: Diseño limpio y mantenible con separación de responsabilidades
- **⚡ Simulación Avanzada**: Sistema de simulación en tiempo real para AGVs
- **📈 Analytics Predictivo**: Predicción de mantenimiento y análisis de rendimiento
- **🚨 Gestión de Emergencias**: Sistema de alertas y paradas de emergencia
- **🌐 API REST**: Endpoints completos para integración externa

---

## 🏛️ Arquitectura del Sistema

```
agv-fleet-commander/
├── domain/              # 🎯 Lógica de Negocio Pura
│   ├── entities.py      #   📦 Entidades del dominio (AGV, Task, Route)
│   ├── ports.py         #   🔌 Interfaces/Contratos
│   └── services.py      #   ⚙️ Servicios de dominio
├── adapters/            # 🔧 Adaptadores Externos
│   ├── data_adapter.py     #   💾 Persistencia de datos (CSV)
│   ├── openai_adapter.py   #   🤖 Integración OpenAI
│   └── notification_adapter.py #   📢 Logging y notificaciones
├── api/                 # 🌐 Capa de Presentación
│   └── main.py          #   FastAPI application
├── data/                # 📊 Datos del Sistema
├── logs/                # 📝 Logs del Sistema
└── config.py            # ⚙️ Configuración
```

### 🔄 Principios de Arquitectura Hexagonal

1. **Dominio Central**: Lógica de negocio independiente de frameworks
2. **Puertos**: Interfaces que definen contratos
3. **Adaptadores**: Implementaciones específicas de tecnología
4. **Inversión de Dependencias**: El dominio no depende de detalles técnicos

---

## 🚀 Instalación y Configuración

### 📋 Prerrequisitos

- Python 3.11+
- OpenAI API Key
- Git

### 🔧 Instalación

```bash
# 1. Clonar repositorio
git clone <repository-url>
cd agv-fleet-commander

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate     # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
export OPENAI_API_KEY="tu-api-key-aqui"
# o crear archivo .env
echo "OPENAI_API_KEY=tu-api-key-aqui" > .env
```

### ⚙️ Configuración Adicional

```bash
# Variables de entorno opcionales
export HOST="localhost"              # Host del servidor
export PORT="5001"                   # Puerto del servidor
export DEBUG="True"                  # Modo debug
export SIMULATION_ENABLED="True"     # Habilitar simulación
export SIMULATION_SPEED="1.0"        # Velocidad de simulación
export LOG_LEVEL="INFO"              # Nivel de logging
```

---

## 🎮 Uso del Sistema

### 🚀 Iniciar el Sistema

```bash
# Método 1: Ejecutar directamente
python main.py

# Método 2: Con uvicorn
uvicorn main:app --host localhost --port 5001 --reload
```

### 🌐 Acceso al Dashboard

- **Dashboard Principal**: http://localhost:5001
- **API Documentation**: http://localhost:5001/api/docs
- **ReDoc**: http://localhost:5001/api/redoc

### 📊 Funcionalidades Principales

#### 1. **Vista General de Flota**
- Estado en tiempo real de todos los AGVs
- Métricas de rendimiento y eficiencia
- Niveles de batería y ubicaciones

#### 2. **Asignación Inteligente de Tareas**
```bash
# Vía API
curl -X POST http://localhost:5001/api/fleet/assign-tasks
```

#### 3. **Optimización de Rutas**
```bash
# Vía API
curl -X POST http://localhost:5001/api/fleet/optimize-routes
```

#### 4. **Control Manual de AGVs**
```bash
# Mover AGV a posición específica
curl -X POST http://localhost:5001/api/agv/move \
  -H "Content-Type: application/json" \
  -d '{
    "agv_id": "AGV-001",
    "position": {"x": 100.0, "y": 200.0}
  }'
```

#### 5. **Parada de Emergencia**
```bash
# Parar AGV inmediatamente
curl -X POST http://localhost:5001/api/agv/AGV-001/emergency-stop
```

---

## 🤖 Integración con OpenAI

### 🧠 Capacidades de IA

1. **Optimización de Rutas**
   - Análisis de tráfico y congestión
   - Optimización energética
   - Evitación de colisiones

2. **Asignación de Tareas**
   - Balanceo de carga de trabajo
   - Consideración de proximidad y batería
   - Priorización inteligente

3. **Análisis Predictivo**
   - Predicción de mantenimiento
   - Análisis de tendencias de rendimiento
   - Generación de insights accionables

### 🔧 Configuración OpenAI

```python
# En config.py
openai_config = OpenAIConfig(
    api_key="tu-api-key",
    model="gpt-4o-mini",
    temperature=0.3,
    max_tokens=2000
)
```

---

## 📊 API Reference

### 🚦 Endpoints Principales

#### Fleet Management
- `GET /api/fleet/overview` - Vista general de la flota
- `POST /api/fleet/assign-tasks` - Asignar tareas con IA
- `POST /api/fleet/optimize-routes` - Optimizar rutas

#### AGV Control
- `POST /api/agv/move` - Mover AGV a posición
- `POST /api/agv/{agv_id}/emergency-stop` - Parada de emergencia

#### AI & Analytics
- `GET /api/ai/insights` - Insights generados por IA

#### System
- `GET /api/system/status` - Estado del sistema
- `GET /api/system/health` - Health check

### 📝 Ejemplos de Respuesta

```json
{
  "fleet_metrics": {
    "total_agvs": 6,
    "active_agvs": 3,
    "idle_agvs": 2,
    "charging_agvs": 1,
    "pending_tasks": 2,
    "completed_tasks": 15,
    "average_battery": 73.5,
    "fleet_efficiency": 0.85
  },
  "agvs": [
    {
      "agv_id": "AGV-001",
      "name": "Alfa Prime",
      "position": {"x": 100.0, "y": 50.0},
      "battery_level": 85.5,
      "status": "IDLE",
      "current_task_id": null
    }
  ]
}
```

---

## 🧪 Testing y Desarrollo

### 🔬 Ejecutar Tests

```bash
# Instalar dependencias de desarrollo
pip install pytest pytest-asyncio

# Ejecutar tests
pytest

# Con coverage
pytest --cov=domain --cov=adapters
```

### 🐛 Debugging

```bash
# Habilitar modo debug
export DEBUG="True"
export LOG_LEVEL="DEBUG"

# Ejecutar con logging detallado
python main.py
```

### 📝 Logs del Sistema

Los logs se almacenan en:
- `logs/agv_system.log` - Log principal del sistema
- `logs/events.json` - Eventos del sistema
- `logs/alerts.json` - Alertas y notificaciones

---

## 🔧 Configuración Avanzada

### 🎛️ Parámetros de AGV

```python
agv_config = AGVConfig(
    max_battery_level=100.0,      # Batería máxima
    min_battery_level=10.0,       # Batería mínima operativa
    charging_threshold=20.0,      # Umbral para cargar
    max_speed_kmh=25.0,          # Velocidad máxima
    max_range_km=50.0,           # Autonomía máxima
    charging_rate_per_minute=2.5  # Velocidad de carga
)
```

### 🚁 Configuración de Flota

```python
fleet_config = FleetConfig(
    max_agvs=20,                     # AGVs máximos
    max_concurrent_tasks=50,         # Tareas concurrentes
    task_timeout_minutes=120,        # Timeout de tareas
    route_optimization_enabled=True, # Optimización IA
    ai_analytics_enabled=True,       # Analytics IA
    maintenance_prediction_enabled=True  # Predicción mantenimiento
)
```

---

## 🔒 Seguridad y Producción

### 🛡️ Consideraciones de Seguridad

1. **API Keys**: Nunca committear claves en el código
2. **Variables de Entorno**: Usar `.env` para configuración sensible
3. **Logging**: No loggear información sensible
4. **CORS**: Configurar orígenes permitidos en producción

### 🚀 Despliegue en Producción

```bash
# Configuración para producción
export DEBUG="False"
export HOST="0.0.0.0"
export PORT="8000"
export LOG_LEVEL="WARNING"

# Usar servidor ASGI para producción
pip install gunicorn[uvicorn]
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

---

## 📈 Monitoreo y Métricas

### 📊 Métricas del Sistema

- **Eficiencia de Flota**: Porcentaje de AGVs productivos
- **Tiempo Promedio de Tarea**: Duración promedio de completar tareas
- **Utilización de Batería**: Consumo energético promedio
- **Tiempo de Respuesta**: Latencia del sistema

### 🚨 Alertas del Sistema

- **Batería Baja**: AGVs con batería < 20%
- **AGV Inactivo**: AGVs sin actividad > 30 minutos
- **Tareas Atrasadas**: Tareas que exceden tiempo límite
- **Predicción de Mantenimiento**: Alertas preventivas

---

## 🤝 Contribución

### 📝 Guías de Contribución

1. **Fork** el repositorio
2. **Crear** una rama para tu feature (`git checkout -b feature/nueva-funcionalidad`)
3. **Commit** tus cambios (`git commit -am 'Agregar nueva funcionalidad'`)
4. **Push** a la rama (`git push origin feature/nueva-funcionalidad`)
5. **Crear** un Pull Request

### 🎯 Estándares de Código

- **PEP 8**: Seguir estándares de Python
- **Type Hints**: Usar anotaciones de tipo
- **Docstrings**: Documentar funciones y clases
- **Tests**: Incluir tests para nuevas funcionalidades

---

## 📚 Documentación Adicional

### 🏗️ Arquitectura Hexagonal
- [Ports & Adapters Pattern](https://alistair.cockburn.us/hexagonal-architecture/)
- [Clean Architecture Principles](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)

### 🤖 OpenAI Integration
- [OpenAI API Documentation](https://platform.openai.com/docs/)
- [GPT-4o mini Guide](https://platform.openai.com/docs/models/gpt-4o-mini)

### ⚡ FastAPI
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Uvicorn Server](https://www.uvicorn.org/)

---

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

---

## 👥 Equipo de Desarrollo

- **Arquitectura**: Diseño hexagonal y patrones DDD
- **IA Integration**: OpenAI GPT-4o mini para optimización
- **Frontend**: Dashboard moderno con Tailwind CSS
- **Backend**: FastAPI con Python 3.11+

---

## 📞 Soporte

Para soporte técnico o consultas:

- **Email**: soporte@agv-fleet-commander.com
- **Issues**: [GitHub Issues](../../issues)
- **Documentación**: [Wiki del Proyecto](../../wiki)

---

**🚀 AGV Fleet Commander - Transformando la logística portuaria con IA**
