# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from airflow.providers.openlineage.utils.spark import (
        inject_parent_job_information_into_spark_properties,
        inject_transport_information_into_spark_properties,
    )
else:
    try:
        from airflow.providers.openlineage.utils.spark import (
            inject_parent_job_information_into_spark_properties,
            inject_transport_information_into_spark_properties,
        )
    except ImportError:
        try:
            from airflow.providers.openlineage.plugins.macros import (
                lineage_job_name,
                lineage_job_namespace,
                lineage_run_id,
            )
        except ImportError:

            def inject_parent_job_information_into_spark_properties(properties: dict, context) -> dict:
                log.warning(
                    "Could not import `airflow.providers.openlineage.plugins.macros`."
                    "Skipping the injection of OpenLineage parent job information into Spark properties."
                )
                return properties

        else:

            def inject_parent_job_information_into_spark_properties(properties: dict, context) -> dict:
                if any(str(key).startswith("spark.openlineage.parent") for key in properties):
                    log.info(
                        "Some OpenLineage properties with parent job information are already present "
                        "in Spark properties. Skipping the injection of OpenLineage "
                        "parent job information into Spark properties."
                    )
                    return properties

                ti = context["ti"]
                ol_parent_job_properties = {
                    "spark.openlineage.parentJobNamespace": lineage_job_namespace(),
                    "spark.openlineage.parentJobName": lineage_job_name(ti),
                    "spark.openlineage.parentRunId": lineage_run_id(ti),
                }
                return {**properties, **ol_parent_job_properties}

        try:
            from airflow.providers.openlineage.plugins.listener import get_openlineage_listener
        except ImportError:

            def inject_transport_information_into_spark_properties(properties: dict, context) -> dict:
                log.warning(
                    "Could not import `airflow.providers.openlineage.plugins.listener`."
                    "Skipping the injection of OpenLineage transport information into Spark properties."
                )
                return properties

        else:

            def inject_transport_information_into_spark_properties(properties: dict, context) -> dict:
                if any(str(key).startswith("spark.openlineage.transport") for key in properties):
                    log.info(
                        "Some OpenLineage properties with transport information are already present "
                        "in Spark properties. Skipping the injection of OpenLineage "
                        "transport information into Spark properties."
                    )
                    return properties

                transport = get_openlineage_listener().adapter.get_or_create_openlineage_client().transport
                if transport.kind != "http":
                    log.info(
                        "OpenLineage transport type `%s` does not support automatic "
                        "injection of OpenLineage transport information into Spark properties.",
                        transport.kind,
                    )
                    return {}

                transport_properties = {
                    "spark.openlineage.transport.type": "http",
                    "spark.openlineage.transport.url": transport.url,
                    "spark.openlineage.transport.endpoint": transport.endpoint,
                    # Timeout is converted to milliseconds, as required by Spark integration,
                    "spark.openlineage.transport.timeoutInMillis": str(int(transport.timeout * 1000)),
                }
                if transport.compression:
                    transport_properties["spark.openlineage.transport.compression"] = str(
                        transport.compression
                    )

                if hasattr(transport.config.auth, "api_key") and transport.config.auth.get_bearer():
                    transport_properties["spark.openlineage.transport.auth.type"] = "api_key"
                    transport_properties["spark.openlineage.transport.auth.apiKey"] = (
                        transport.config.auth.get_bearer()
                    )

                if hasattr(transport.config, "custom_headers") and transport.config.custom_headers:
                    for key, value in transport.config.custom_headers.items():
                        transport_properties[f"spark.openlineage.transport.headers.{key}"] = value

                return {**properties, **transport_properties}


__all__ = [
    "inject_parent_job_information_into_spark_properties",
    "inject_transport_information_into_spark_properties",
]
