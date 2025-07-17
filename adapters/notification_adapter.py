"""
Notification Adapter - AGV Fleet Commander
Adaptador para logging y notificaciones del sistema
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from dataclasses import asdict

from domain.ports import NotificationPort


class LoggingNotificationAdapter(NotificationPort):
    """
    Adaptador para logging y notificaciones usando archivos y consola
    """

    def __init__(self, log_directory: str = "logs"):
        self.log_directory = Path(log_directory)
        self.log_directory.mkdir(exist_ok=True)

        # Configurar logging
        self.logger = self._setup_logger()

        # Archivos de eventos y alertas
        self.events_file = self.log_directory / "events.json"
        self.alerts_file = self.log_directory / "alerts.json"

        # Almacenamiento en memoria para consulta rápida
        self._recent_events = []
        self._recent_alerts = []

        # Cargar eventos existentes
        self._load_existing_data()

    def _setup_logger(self) -> logging.Logger:
        """Configurar logger del sistema"""
        logger = logging.getLogger("agv_fleet_commander")
        logger.setLevel(logging.INFO)

        # Evitar duplicar handlers
        if not logger.handlers:
            # Handler para archivo
            file_handler = logging.FileHandler(
                self.log_directory / "agv_system.log", encoding="utf-8"
            )
            file_handler.setLevel(logging.INFO)

            # Handler para consola
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.WARNING)

            # Formato
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)

            logger.addHandler(file_handler)
            logger.addHandler(console_handler)

        return logger

    def _load_existing_data(self):
        """Cargar eventos y alertas existentes"""
        # Cargar eventos
        if self.events_file.exists():
            try:
                with open(self.events_file, "r", encoding="utf-8") as f:
                    self._recent_events = json.load(f)
                    # Mantener solo los últimos 100 eventos
                    self._recent_events = self._recent_events[-100:]
            except Exception as e:
                self.logger.error(f"Error cargando eventos: {e}")
                self._recent_events = []

        # Cargar alertas
        if self.alerts_file.exists():
            try:
                with open(self.alerts_file, "r", encoding="utf-8") as f:
                    self._recent_alerts = json.load(f)
                    # Mantener solo las últimas 50 alertas
                    self._recent_alerts = self._recent_alerts[-50:]
            except Exception as e:
                self.logger.error(f"Error cargando alertas: {e}")
                self._recent_alerts = []

    def _save_events(self):
        """Guardar eventos a archivo"""
        try:
            with open(self.events_file, "w", encoding="utf-8") as f:
                json.dump(self._recent_events, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Error guardando eventos: {e}")

    def _save_alerts(self):
        """Guardar alertas a archivo"""
        try:
            with open(self.alerts_file, "w", encoding="utf-8") as f:
                json.dump(self._recent_alerts, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Error guardando alertas: {e}")

    def log_event(self, event_type: str, data: Dict[str, Any]) -> bool:
        """Registrar evento del sistema"""
        try:
            event = {
                "event_id": f"EVT_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
                "event_type": event_type,
                "timestamp": datetime.now().isoformat(),
                "data": data,
                "source": "agv_fleet_commander",
            }

            # Agregar a memoria
            self._recent_events.append(event)

            # Mantener solo los últimos 100 eventos
            if len(self._recent_events) > 100:
                self._recent_events.pop(0)

            # Guardar a archivo
            self._save_events()

            # Log según tipo de evento
            log_message = f"Evento {event_type}: {json.dumps(data, ensure_ascii=False)}"

            if event_type in ["task_assigned", "agv_status_change", "route_optimized"]:
                self.logger.info(log_message)
            elif event_type in ["manual_agv_move", "emergency_task_created"]:
                self.logger.warning(log_message)
            else:
                self.logger.info(log_message)

            return True

        except Exception as e:
            self.logger.error(f"Error registrando evento: {e}")
            return False

    def send_alert(self, message: str, severity: str = "medium") -> bool:
        """Enviar alerta del sistema"""
        try:
            alert = {
                "alert_id": f"ALT_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
                "message": message,
                "severity": severity.upper(),
                "timestamp": datetime.now().isoformat(),
                "acknowledged": False,
                "source": "agv_fleet_commander",
            }

            # Agregar a memoria
            self._recent_alerts.append(alert)

            # Mantener solo las últimas 50 alertas
            if len(self._recent_alerts) > 50:
                self._recent_alerts.pop(0)

            # Guardar a archivo
            self._save_alerts()

            # Log según severidad
            if severity.upper() in ["HIGH", "CRITICAL", "URGENT"]:
                self.logger.error(f"🚨 ALERTA {severity.upper()}: {message}")
            elif severity.upper() == "MEDIUM":
                self.logger.warning(f"⚠️ ALERTA {severity.upper()}: {message}")
            else:
                self.logger.info(f"ℹ️ ALERTA {severity.upper()}: {message}")

            return True

        except Exception as e:
            self.logger.error(f"Error enviando alerta: {e}")
            return False

    def get_recent_events(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Obtener eventos recientes"""
        return self._recent_events[-limit:] if self._recent_events else []

    def get_recent_alerts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Obtener alertas recientes"""
        return self._recent_alerts[-limit:] if self._recent_alerts else []

    def get_unacknowledged_alerts(self) -> List[Dict[str, Any]]:
        """Obtener alertas no reconocidas"""
        return [
            alert
            for alert in self._recent_alerts
            if not alert.get("acknowledged", False)
        ]

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Marcar alerta como reconocida"""
        try:
            for alert in self._recent_alerts:
                if alert["alert_id"] == alert_id:
                    alert["acknowledged"] = True
                    alert["acknowledged_at"] = datetime.now().isoformat()
                    self._save_alerts()
                    self.logger.info(f"Alerta {alert_id} reconocida")
                    return True
            return False
        except Exception as e:
            self.logger.error(f"Error reconociendo alerta: {e}")
            return False

    def get_system_status(self) -> Dict[str, Any]:
        """Obtener estado del sistema de notificaciones"""
        total_events = len(self._recent_events)
        total_alerts = len(self._recent_alerts)
        unack_alerts = len(self.get_unacknowledged_alerts())

        # Contar eventos por tipo
        event_types = {}
        for event in self._recent_events:
            event_type = event.get("event_type", "unknown")
            event_types[event_type] = event_types.get(event_type, 0) + 1

        # Contar alertas por severidad
        alert_severity = {}
        for alert in self._recent_alerts:
            severity = alert.get("severity", "UNKNOWN")
            alert_severity[severity] = alert_severity.get(severity, 0) + 1

        return {
            "system_status": "OPERATIONAL",
            "last_update": datetime.now().isoformat(),
            "events": {"total": total_events, "by_type": event_types},
            "alerts": {
                "total": total_alerts,
                "unacknowledged": unack_alerts,
                "by_severity": alert_severity,
            },
            "storage": {
                "events_file": str(self.events_file),
                "alerts_file": str(self.alerts_file),
                "log_file": str(self.log_directory / "agv_system.log"),
            },
        }


class ConsoleNotificationAdapter(NotificationPort):
    """
    Adaptador simple para notificaciones por consola (desarrollo/testing)
    """

    def __init__(self):
        self.events = []
        self.alerts = []

    def log_event(self, event_type: str, data: Dict[str, Any]) -> bool:
        """Registrar evento en consola"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        event = {"timestamp": timestamp, "type": event_type, "data": data}
        self.events.append(event)

        print(
            f"📋 [{timestamp}] EVENTO {event_type.upper()}: {json.dumps(data, ensure_ascii=False)}"
        )
        return True

    def send_alert(self, message: str, severity: str = "medium") -> bool:
        """Enviar alerta por consola"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        alert = {
            "timestamp": timestamp,
            "message": message,
            "severity": severity.upper(),
        }
        self.alerts.append(alert)

        # Iconos según severidad
        icons = {
            "LOW": "ℹ️",
            "MEDIUM": "⚠️",
            "HIGH": "🚨",
            "CRITICAL": "🔥",
            "URGENT": "💥",
        }

        icon = icons.get(severity.upper(), "📢")
        print(f"{icon} [{timestamp}] ALERTA {severity.upper()}: {message}")
        return True

    def get_recent_events(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Obtener eventos recientes"""
        return self.events[-limit:] if self.events else []

    def get_recent_alerts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Obtener alertas recientes"""
        return self.alerts[-limit:] if self.alerts else []

    def get_unacknowledged_alerts(self) -> List[Dict[str, Any]]:
        """Obtener alertas no reconocidas (todas en este adaptador)"""
        return self.alerts

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Marcar alerta como reconocida (no implementado)"""
        print(f"✅ Alerta {alert_id} reconocida")
        return True

    def get_system_status(self) -> Dict[str, Any]:
        """Obtener estado del sistema"""
        return {
            "system_status": "CONSOLE_MODE",
            "total_events": len(self.events),
            "total_alerts": len(self.alerts),
            "last_update": datetime.now().isoformat(),
        }
