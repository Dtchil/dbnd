from distutils.version import LooseVersion

import airflow


def make_safe_label_value(value):
    if LooseVersion(airflow.version.version) > LooseVersion("1.10.10"):
        from airflow.kubernetes.pod_generator import (
            make_safe_label_value as airflow_make_safe_label_value,
        )

        return airflow_make_safe_label_value(value)

    from airflow.contrib.executors.kubernetes_executor import AirflowKubernetesScheduler

    return AirflowKubernetesScheduler._make_safe_label_value(value)
