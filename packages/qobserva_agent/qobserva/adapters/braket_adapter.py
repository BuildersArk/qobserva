from __future__ import annotations

from typing import Any, Dict
from .base import Adapter, AdapterContext
from .version_utils import get_sdk_version

class BraketAdapter(Adapter):
    name = "braket"
    priority = 80

    def can_handle(self, obj: Any, context: AdapterContext) -> bool:
        return (
            "braket" in obj.__class__.__module__
            or hasattr(obj, "measurement_counts")
            or (isinstance(obj, dict) and obj.get("provider") == "aws_braket")
        )

    def extract(self, obj: Any, context: AdapterContext) -> Dict[str, Any]:
        histogram = {}
        if hasattr(obj, "measurement_counts"):
            try:
                histogram = {str(k): int(v) for k, v in dict(obj.measurement_counts).items()}
            except Exception:
                histogram = {}
        if not histogram and isinstance(obj, dict) and "counts" in obj:
            histogram = {str(k): int(v) for k, v in obj["counts"].items()}

        shots = sum(histogram.values()) or 1

        # Extract backend info from result object - try multiple methods
        backend_name = None
        provider = None
        
        # Method 1: Check task_metadata for device ARN (most reliable for real devices)
        if hasattr(obj, "task_metadata"):
            try:
                metadata = obj.task_metadata
                if isinstance(metadata, dict):
                    device_arn = metadata.get("deviceArn", "")
                    if device_arn:
                        # Extract device name from ARN
                        # e.g., "arn:aws:braket:::device/quantum-simulator/amazon/sv1" -> "sv1"
                        # e.g., "arn:aws:braket:::device/qpu/ionq/ionQdevice" -> "ionQdevice"
                        parts = device_arn.split("/")
                        if len(parts) > 0 and parts[-1]:
                            backend_name = parts[-1]
                            # Determine provider from ARN structure
                            if "/quantum-simulator/" in device_arn or "/simulator/" in device_arn:
                                provider = "local_sim"
                            elif "/qpu/" in device_arn:
                                # Extract provider from ARN (e.g., ionq, rigetti, oqc)
                                if len(parts) >= 2:
                                    provider_name = parts[-2].lower()
                                    if provider_name in ["ionq", "rigetti", "oqc", "quera"]:
                                        provider = provider_name
                                    else:
                                        provider = "aws_braket"  # AWS managed device
                                else:
                                    provider = "aws_braket"
                            else:
                                provider = "aws_braket"
            except Exception:
                pass
        
        # Method 2: Check for device attribute directly
        if not backend_name and hasattr(obj, "device"):
            try:
                device = obj.device
                if hasattr(device, "name"):
                    backend_name = str(device.name)
                elif hasattr(device, "id"):
                    backend_name = str(device.id)
                elif hasattr(device, "__str__"):
                    backend_name = str(device)
                # Check device type
                if backend_name:
                    device_str = backend_name.lower()
                    if "local" in device_str or "simulator" in device_str:
                        provider = provider or "local_sim"
                    else:
                        provider = provider or "aws_braket"
            except Exception:
                pass
        
        # Method 3: Check result type/class name for simulator indication
        if not backend_name:
            try:
                class_name = obj.__class__.__name__.lower()
                module_name = obj.__class__.__module__.lower()
                if "local" in class_name or "local" in module_name:
                    backend_name = "LocalSimulator"
                    provider = provider or "local_sim"
            except Exception:
                pass
        
        # Method 4: Check if this is a LocalSimulator result (no device ARN means local)
        if not backend_name:
            # If we have measurement_counts but no device info, it's likely LocalSimulator
            if hasattr(obj, "measurement_counts") and histogram:
                backend_name = "LocalSimulator"
                provider = provider or "local_sim"
        
        # Fallback only if we truly can't determine backend
        if not backend_name:
            # Default to LocalSimulator for local testing (most common case)
            backend_name = "LocalSimulator"
        if not provider:
            provider = "local_sim"  # Default to local_sim for unknown (most tests use simulators)

        return {
            "sdk": {"name": "braket", "version": get_sdk_version("braket")},
            "backend": {"provider": provider, "name": backend_name},
            "shots": shots,
            "artifacts": {"result_type": "counts", "counts": {"bit_order": "little", "histogram": histogram, "mapping": {}}},
        }
