from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FrequencyConstantsConfig:
    number_of_constants: int
    f_i: list[float]
    delta_f_i: list[float]
    delta_A_i: list[float]


@dataclass(frozen=True, slots=True)
class LineConfig:
    symmetrical: list[str]
    asymmetrical: list[str]
    power: list[str]


@dataclass(frozen=True, slots=True)
class NormParamsConfig:
    delta_stn: list[float]
    w_n: list[float]


@dataclass(frozen=True, slots=True)
class AppConfig:
    frequency_constants: FrequencyConstantsConfig
    norm_params: NormParamsConfig
    lines: LineConfig
    operation_modes: list[str]


@dataclass(frozen=True, slots=True)
class MeasurementPoint:
    index: int
    delta_f: float
    f: float
    u_sn: float
    u_n: float
    u_s: float
    q: float
    is_violation: bool


@dataclass(frozen=True, slots=True)
class CalculationResult:
    points: list[MeasurementPoint]
    has_violations: bool
