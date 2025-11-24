"""Alert system for critical events."""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional
from datetime import datetime

from loguru import logger

from config.settings import Settings


class AlertSystem:
    """Sends alerts for critical trading events."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.alert_history: List[Dict] = []

    async def send_alert(
        self, level: str, message: str, data: Dict = None
    ) -> None:
        """
        Send an alert.

        Args:
            level: Alert level (INFO, WARNING, CRITICAL)
            message: Alert message
            data: Additional data
        """
        alert = {
            "level": level,
            "message": message,
            "data": data or {},
            "timestamp": datetime.now().isoformat(),
        }

        self.alert_history.append(alert)

        # Log the alert
        if level == "CRITICAL":
            logger.critical(f"ALERT: {message}")
        elif level == "WARNING":
            logger.warning(f"ALERT: {message}")
        else:
            logger.info(f"ALERT: {message}")

        # Send email if enabled and level is WARNING or CRITICAL
        if self.settings.alert_email_enabled and level in ["WARNING", "CRITICAL"]:
            try:
                await self._send_email(level, message, data)
            except Exception as e:
                logger.error(f"Failed to send email alert: {e}", exc_info=True)

    async def alert_daily_loss_limit(self, daily_pnl: float, limit: float) -> None:
        """Alert when approaching daily loss limit."""
        percentage = (abs(daily_pnl) / limit) * 100
        await self.send_alert(
            "CRITICAL",
            f"Daily loss limit approaching: ${abs(daily_pnl):.2f} ({percentage:.1f}%)",
            {"daily_pnl": daily_pnl, "limit": limit},
        )

    async def alert_max_drawdown(self, distance_to_limit: float) -> None:
        """Alert when approaching max drawdown."""
        await self.send_alert(
            "CRITICAL",
            f"Trailing max drawdown approaching: ${distance_to_limit:.2f} remaining",
            {"distance_to_limit": distance_to_limit},
        )

    async def alert_api_error(self, error: str) -> None:
        """Alert on API errors."""
        await self.send_alert(
            "WARNING",
            f"API Error: {error}",
            {"error": error},
        )

    async def alert_position_closed(self, position_id: str, reason: str) -> None:
        """Alert when position is closed."""
        await self.send_alert(
            "INFO",
            f"Position closed: {position_id} - {reason}",
            {"position_id": position_id, "reason": reason},
        )
    
    async def _send_email(self, level: str, message: str, data: Optional[Dict] = None) -> None:
        """Send email alert."""
        if not self.settings.alert_email_to:
            logger.warning("Email alerts enabled but no recipient configured")
            return
        
        try:
            msg = MIMEMultipart()
            msg["From"] = self.settings.alert_email_username
            msg["To"] = self.settings.alert_email_to
            msg["Subject"] = f"[{level}] TopstepX Trading Bot Alert"
            
            body = f"""
Trading Bot Alert

Level: {level}
Message: {message}
Time: {datetime.now().isoformat()}
"""
            if data:
                body += "\nAdditional Data:\n"
                for key, value in data.items():
                    body += f"  {key}: {value}\n"
            
            msg.attach(MIMEText(body, "plain"))
            
            with smtplib.SMTP(self.settings.alert_email_smtp_host, self.settings.alert_email_smtp_port) as server:
                server.starttls()
                server.login(self.settings.alert_email_username, self.settings.alert_email_password)
                server.send_message(msg)
            
            logger.info(f"Email alert sent to {self.settings.alert_email_to}")
            
        except Exception as e:
            logger.error(f"Error sending email: {e}", exc_info=True)
            raise

