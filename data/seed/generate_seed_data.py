"""Generate synthetic FHIR R4 seed data with Argentine demographics.

Produces a Transaction Bundle with ~200 patients and 10 resource types
(Patient, Condition, Observation, MedicationRequest, Encounter, Procedure,
AllergyIntolerance, Immunization, DiagnosticReport, CarePlan) using realistic
Argentine names, DNI, provinces, and SNOMED CT / LOINC / ATC / CVX codes.

Usage:
    python generate_seed_data.py [output_path]

Requires only Python stdlib (no external dependencies).
"""

from __future__ import annotations

import json
import random
import sys
import uuid
from datetime import date, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Deterministic seed for reproducibility
# ---------------------------------------------------------------------------
random.seed(42)

# ---------------------------------------------------------------------------
# Argentine demographic data
# ---------------------------------------------------------------------------

FIRST_NAMES_MALE = [
    "Juan",
    "Carlos",
    "José",
    "Luis",
    "Miguel",
    "Jorge",
    "Pablo",
    "Diego",
    "Martín",
    "Alejandro",
    "Ricardo",
    "Fernando",
    "Daniel",
    "Sergio",
    "Roberto",
    "Eduardo",
    "Raúl",
    "Héctor",
    "Oscar",
    "Mario",
    "Gustavo",
    "Andrés",
    "Marcelo",
    "Nicolás",
    "Santiago",
    "Matías",
    "Facundo",
    "Leandro",
    "Tomás",
    "Agustín",
]

FIRST_NAMES_FEMALE = [
    "María",
    "Ana",
    "Laura",
    "Lucía",
    "Marta",
    "Silvia",
    "Patricia",
    "Claudia",
    "Gabriela",
    "Valentina",
    "Florencia",
    "Carolina",
    "Camila",
    "Julieta",
    "Sofía",
    "Victoria",
    "Romina",
    "Daniela",
    "Andrea",
    "Verónica",
    "Graciela",
    "Liliana",
    "Soledad",
    "Celeste",
    "Milagros",
    "Rocío",
    "Natalia",
    "Mariana",
    "Paula",
    "Eugenia",
]

LAST_NAMES = [
    "González",
    "Rodríguez",
    "Gómez",
    "Fernández",
    "López",
    "Díaz",
    "Martínez",
    "Pérez",
    "García",
    "Sánchez",
    "Romero",
    "Sosa",
    "Álvarez",
    "Torres",
    "Ruiz",
    "Ramírez",
    "Flores",
    "Acosta",
    "Medina",
    "Benítez",
    "Herrera",
    "Suárez",
    "Aguirre",
    "Castro",
    "Ríos",
    "Ortiz",
    "Luna",
    "Juárez",
    "Cabrera",
    "Morales",
]

# Provinces weighted roughly by population proportion
PROVINCES = [
    ("Buenos Aires", "B", 0.40),
    ("Ciudad Autónoma de Buenos Aires", "C", 0.08),
    ("Córdoba", "X", 0.09),
    ("Santa Fe", "S", 0.08),
    ("Mendoza", "M", 0.05),
    ("Tucumán", "T", 0.04),
    ("Entre Ríos", "E", 0.03),
    ("Salta", "A", 0.03),
    ("Chaco", "H", 0.03),
    ("Misiones", "N", 0.03),
    ("Santiago del Estero", "G", 0.02),
    ("Corrientes", "W", 0.02),
    ("San Juan", "J", 0.02),
    ("Jujuy", "Y", 0.02),
    ("Río Negro", "R", 0.02),
    ("Neuquén", "Q", 0.02),
    ("Formosa", "P", 0.01),
    ("San Luis", "D", 0.01),
]

# ---------------------------------------------------------------------------
# SNOMED CT codes for conditions prevalent in Argentina
# (code, display_es, display_en, prevalence_weight)
# Weights are relative (normalized by random.choices).
# ---------------------------------------------------------------------------
CONDITIONS = [
    ("44054006", "Diabetes mellitus tipo 2", "Type 2 diabetes mellitus", 0.20),
    ("59621000", "Hipertensión arterial esencial", "Essential hypertension", 0.25),
    ("77506005", "Enfermedad de Chagas", "Chagas disease", 0.05),
    ("38362002", "Dengue", "Dengue", 0.04),
    ("195967001", "Asma", "Asthma", 0.08),
    ("13645005", "Enfermedad pulmonar obstructiva crónica", "COPD", 0.06),
    ("73211009", "Diabetes mellitus tipo 1", "Type 1 diabetes mellitus", 0.03),
    ("22298006", "Infarto agudo de miocardio", "Myocardial infarction", 0.04),
    ("84114007", "Insuficiencia cardíaca", "Heart failure", 0.05),
    ("56265001", "Enfermedad cardíaca reumática", "Rheumatic heart disease", 0.02),
    ("235856003", "Hepatitis viral", "Viral hepatitis", 0.02),
    ("56717001", "Tuberculosis", "Tuberculosis", 0.03),
    ("414545008", "Cardiopatía isquémica", "Ischemic heart disease", 0.04),
    ("267036007", "Anemia ferropénica", "Iron deficiency anemia", 0.05),
    ("46635009", "Diabetes mellitus tipo 1 con cetoacidosis", "Type 1 DM with ketoacidosis", 0.01),
    ("49436004", "Fibrilación auricular", "Atrial fibrillation", 0.03),
    # New conditions (Sprint 5.1)
    ("190331003", "Hipotiroidismo", "Hypothyroidism", 0.06),
    ("35489007", "Depresión", "Depression", 0.07),
    ("398102009", "Obesidad", "Obesity", 0.08),
    ("40055000", "Enfermedad renal crónica", "Chronic kidney disease", 0.04),
    ("230690007", "Accidente cerebrovascular", "Stroke", 0.03),
]

# ---------------------------------------------------------------------------
# LOINC observation types with normal/abnormal ranges
# (loinc_code, display_es, unit, normal_low, normal_high,
#  abnormal_low, abnormal_high, related_condition_snomed)
# When related_condition_snomed is present and patient has that condition,
# abnormal range is used; otherwise normal range.
# ---------------------------------------------------------------------------
OBSERVATION_TYPES = [
    ("2345-7", "Glucosa en sangre", "mg/dL", 70, 110, 140, 300, "44054006"),
    ("718-7", "Hemoglobina", "g/dL", 12.0, 17.0, 6.0, 10.0, "267036007"),
    ("8480-6", "Presión arterial sistólica", "mmHg", 110, 130, 140, 180, "59621000"),
    ("8462-4", "Presión arterial diastólica", "mmHg", 60, 80, 90, 110, "59621000"),
    ("2093-3", "Colesterol total", "mg/dL", 150, 200, 220, 300, None),
    ("4548-4", "Hemoglobina glicosilada", "%", 4.0, 5.6, 7.0, 12.0, "44054006"),
    # New observations (Sprint 5.1)
    ("2160-0", "Creatinina", "mg/dL", 0.6, 1.2, 2.5, 8.0, "40055000"),
    ("2571-8", "Triglicéridos", "mg/dL", 50, 150, 200, 500, None),
    ("3016-3", "TSH", "mIU/L", 0.4, 4.0, 8.0, 50.0, "190331003"),
    ("6690-2", "Leucocitos", "x10^3/uL", 4.5, 11.0, 12.0, 25.0, None),
]

# ---------------------------------------------------------------------------
# Medications (ATC codes) with associated conditions
# (atc_code, display_es, [associated_snomed_codes])
# ---------------------------------------------------------------------------
MEDICATIONS = [
    ("A10BA02", "Metformina 850mg", ["44054006"]),
    ("C09AA02", "Enalapril 10mg", ["59621000"]),
    ("C09CA01", "Losartán 50mg", ["59621000"]),
    ("C07AB03", "Atenolol 50mg", ["59621000"]),
    ("B01AC06", "Aspirina 100mg", []),
    ("A02BC01", "Omeprazol 20mg", []),
    ("A10AC01", "Insulina NPH", ["44054006", "73211009"]),
    ("R03AC02", "Salbutamol inhalatorio", ["195967001"]),
    ("H03AA01", "Levotiroxina 50mcg", ["190331003"]),
    ("C08CA01", "Amlodipina 5mg", ["59621000"]),
    # New medications (Sprint 5.1)
    ("N06AB06", "Sertralina 50mg", ["35489007"]),
    ("C10AA05", "Atorvastatina 20mg", []),
    ("B01AC04", "Clopidogrel 75mg", ["22298006", "414545008"]),
]

# ---------------------------------------------------------------------------
# Encounter class codes (HL7 v3 ActCode)
# (code, display_es, weight)
# ---------------------------------------------------------------------------
ENCOUNTER_TYPES = [
    ("AMB", "Consulta ambulatoria", 0.55),
    ("EMER", "Guardia / Urgencias", 0.20),
    ("IMP", "Internación", 0.15),
    ("HH", "Visita domiciliaria", 0.10),
]

# ---------------------------------------------------------------------------
# Procedures (SNOMED CT) — new in Sprint 5.1
# (code, display_es, [required_condition_snomeds], female_only, weight)
# If required_condition_snomeds is non-empty, procedure only applies to
# patients with at least one of those conditions.
# ---------------------------------------------------------------------------
PROCEDURES = [
    ("80146002", "Apendicectomía", [], False, 0.08),
    ("73761001", "Colecistectomía", ["39621005"], False, 0.07),
    ("11466000", "Cesárea", [], True, 0.06),
    ("108241001", "Diálisis", ["40055000"], False, 0.12),
    ("86273004", "Biopsia", [], False, 0.08),
    ("232717009", "Coronariografía", ["414545008", "22298006", "84114007"], False, 0.12),
    ("397956004", "Endoscopía digestiva alta", [], False, 0.08),
    ("274025005", "Colocación de stent coronario", ["414545008", "22298006"], False, 0.08),
    ("422073006", "Cirugía de cataratas", [], False, 0.06),
    ("65546002", "Extracción dental", [], False, 0.08),
]

# ---------------------------------------------------------------------------
# Allergies (SNOMED CT) — new in Sprint 5.1
# (code, display_es, category, weight)
# category: medication | food | environment
# ---------------------------------------------------------------------------
ALLERGIES = [
    ("91936005", "Alergia a penicilina", "medication", 0.25),
    ("294505008", "Alergia a antiinflamatorios no esteroideos", "medication", 0.15),
    ("300913006", "Alergia al látex", "environment", 0.10),
    ("91935009", "Alergia al maní", "food", 0.10),
    ("414285001", "Alergia a alimentos", "food", 0.10),
    ("418689008", "Alergia al huevo", "food", 0.08),
    ("294183002", "Alergia a la aspirina", "medication", 0.07),
    ("419474003", "Alergia al polen", "environment", 0.15),
]

# ---------------------------------------------------------------------------
# Vaccines (CVX codes) — new in Sprint 5.1
# Argentine national vaccination calendar.
# (cvx_code, display_es, display_en, weight)
# ---------------------------------------------------------------------------
VACCINES = [
    ("19", "BCG", "BCG vaccine", 0.15),
    ("08", "Hepatitis B", "Hepatitis B vaccine", 0.15),
    ("20", "DTP (triple bacteriana)", "DTaP vaccine", 0.12),
    ("10", "IPV (Salk)", "Inactivated poliovirus vaccine", 0.12),
    ("03", "Triple viral (SRP)", "MMR vaccine", 0.12),
    ("15", "Antigripal", "Influenza vaccine", 0.15),
    ("213", "COVID-19", "COVID-19 vaccine", 0.12),
    ("133", "Neumococo conjugada", "Pneumococcal conjugate vaccine", 0.07),
]

# ---------------------------------------------------------------------------
# Diagnostic report types (LOINC panel codes) — new in Sprint 5.1
# (loinc_code, display_es, display_en, component_loincs, weight)
# component_loincs: LOINC codes of observations that belong to this panel.
# ---------------------------------------------------------------------------
DIAGNOSTIC_REPORT_TYPES = [
    (
        "58410-2",
        "Hemograma completo",
        "Complete blood count",
        ["718-7", "6690-2"],
        0.30,
    ),
    (
        "24331-1",
        "Panel lipídico",
        "Lipid panel",
        ["2093-3", "2571-8"],
        0.25,
    ),
    (
        "24325-3",
        "Hepatograma",
        "Hepatic function panel",
        [],
        0.15,
    ),
    (
        "24323-8",
        "Panel metabólico",
        "Comprehensive metabolic panel",
        ["2345-7", "2160-0"],
        0.20,
    ),
    (
        "30954-2",
        "Perfil tiroideo",
        "Thyroid function panel",
        ["3016-3"],
        0.10,
    ),
]


# ---------------------------------------------------------------------------
# CarePlan categories + titles — new in Sprint 5.3
# Maps SNOMED condition codes → (title_es, SNOMED category code, category display)
# Used to generate clinically coherent care plans that address existing conditions.
# ---------------------------------------------------------------------------
CAREPLAN_TEMPLATES: dict[str, tuple[str, str, str]] = {
    "44054006": (
        "Plan de manejo de diabetes mellitus tipo 2",
        "698360004",
        "Diabetes self-management plan",
    ),
    "59621000": (
        "Plan de control de hipertensión arterial",
        "734163000",
        "Hypertension clinical management plan",
    ),
    "195967001": (
        "Plan de manejo del asma",
        "710916007",
        "Asthma clinical management plan",
    ),
    "13645005": (
        "Plan de rehabilitación pulmonar (EPOC)",
        "390864007",
        "COPD clinical management plan",
    ),
    "84114007": (
        "Plan de manejo de insuficiencia cardíaca",
        "735984001",
        "Heart failure self-management plan",
    ),
    "40055000": (
        "Plan de manejo de enfermedad renal crónica",
        "736285004",
        "Kidney disease clinical management plan",
    ),
    "35489007": (
        "Plan de tratamiento de depresión",
        "736253002",
        "Mental health care plan",
    ),
    "398102009": (
        "Plan de manejo de obesidad",
        "408289007",
        "Obesity management plan",
    ),
    "190331003": (
        "Plan de manejo de hipotiroidismo",
        "709137006",
        "Hypothyroidism clinical management plan",
    ),
    "73211009": (
        "Plan de manejo de diabetes mellitus tipo 1",
        "698360004",
        "Diabetes self-management plan",
    ),
}

# Fallback for conditions without a specific template
CAREPLAN_GENERIC = (
    "Plan de cuidado general",
    "734163000",
    "Care plan",
)

CAREPLAN_STATUSES = [
    ("active", 0.65),
    ("completed", 0.15),
    ("on-hold", 0.10),
    ("revoked", 0.10),
]


def _weighted_choice(items: list[tuple], weight_index: int = -1) -> tuple:
    """Select from items using the weight at weight_index."""
    weights = [item[weight_index] for item in items]
    return random.choices(items, weights=weights, k=1)[0]


def _generate_dni() -> str:
    """Generate a realistic Argentine DNI number (8 digits)."""
    return str(random.randint(10_000_000, 45_000_000))


def _random_birth_date(min_age: int = 1, max_age: int = 90) -> str:
    """Generate a random birth date as YYYY-MM-DD string."""
    today = date(2025, 1, 1)  # Fixed reference date for reproducibility
    age_days = random.randint(min_age * 365, max_age * 365)
    birth = today - timedelta(days=age_days)
    return birth.isoformat()


def _random_condition_date(birth_date_str: str) -> str:
    """Generate a condition onset date after birth but before reference date."""
    birth = date.fromisoformat(birth_date_str)
    reference = date(2025, 1, 1)
    if birth >= reference:
        return reference.isoformat()
    days_alive = (reference - birth).days
    # Conditions onset typically in adulthood or later childhood
    min_onset = max(int(days_alive * 0.2), 365)
    onset_days = random.randint(min_onset, days_alive)
    onset = birth + timedelta(days=onset_days)
    return onset.isoformat()


def _random_recent_date(years_back: int = 2) -> str:
    """Generate a random date within the last N years from reference date."""
    reference = date(2025, 1, 1)
    days_back = random.randint(1, years_back * 365)
    d = reference - timedelta(days=days_back)
    return d.isoformat()


def generate_patient(patient_uuid: str) -> dict:
    """Generate a single FHIR Patient resource."""
    gender = random.choice(["male", "female"])
    if gender == "male":
        given = random.choice(FIRST_NAMES_MALE)
    else:
        given = random.choice(FIRST_NAMES_FEMALE)

    family = random.choice(LAST_NAMES)
    province_name, _province_code, _ = _weighted_choice(PROVINCES)
    dni = _generate_dni()
    birth_date = _random_birth_date(min_age=5, max_age=85)

    return {
        "resourceType": "Patient",
        "identifier": [
            {
                "system": "http://www.renaper.gob.ar/dni",
                "value": dni,
            }
        ],
        "name": [
            {
                "use": "official",
                "family": family,
                "given": [given],
            }
        ],
        "gender": gender,
        "birthDate": birth_date,
        "address": [
            {
                "use": "home",
                "state": province_name,
                "country": "AR",
            }
        ],
    }


def generate_condition(
    condition_uuid: str,
    patient_uuid: str,
    patient_birth_date: str,
    snomed_code: str,
    display: str,
) -> dict:
    """Generate a single FHIR Condition resource."""
    onset = _random_condition_date(patient_birth_date)
    clinical_status = random.choices(["active", "resolved"], weights=[0.8, 0.2], k=1)[0]

    return {
        "resourceType": "Condition",
        "clinicalStatus": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                    "code": clinical_status,
                }
            ]
        },
        "verificationStatus": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                    "code": "confirmed",
                }
            ]
        },
        "code": {
            "coding": [
                {
                    "system": "http://snomed.info/sct",
                    "code": snomed_code,
                    "display": display,
                }
            ],
            "text": display,
        },
        "subject": {
            "reference": f"urn:uuid:{patient_uuid}",
        },
        "onsetDateTime": onset,
    }


def generate_observation(
    obs_uuid: str,
    patient_uuid: str,
    loinc_code: str,
    display: str,
    value: float,
    unit: str,
    effective_date: str,
) -> dict:
    """Generate a single FHIR Observation resource."""
    return {
        "resourceType": "Observation",
        "status": "final",
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": loinc_code,
                    "display": display,
                }
            ],
            "text": display,
        },
        "subject": {
            "reference": f"urn:uuid:{patient_uuid}",
        },
        "effectiveDateTime": effective_date,
        "valueQuantity": {
            "value": round(value, 1),
            "unit": unit,
            "system": "http://unitsofmeasure.org",
            "code": unit,
        },
    }


def generate_medication_request(
    med_uuid: str,
    patient_uuid: str,
    atc_code: str,
    display: str,
    status: str,
    authored_date: str,
) -> dict:
    """Generate a single FHIR MedicationRequest resource."""
    return {
        "resourceType": "MedicationRequest",
        "status": status,
        "intent": "order",
        "medicationCodeableConcept": {
            "coding": [
                {
                    "system": "http://www.whocc.no/atc",
                    "code": atc_code,
                    "display": display,
                }
            ],
            "text": display,
        },
        "subject": {
            "reference": f"urn:uuid:{patient_uuid}",
        },
        "authoredOn": authored_date,
    }


def generate_encounter(
    enc_uuid: str,
    patient_uuid: str,
    class_code: str,
    class_display: str,
    period_start: str,
    period_end: str,
) -> dict:
    """Generate a single FHIR Encounter resource."""
    return {
        "resourceType": "Encounter",
        "status": "finished",
        "class": {
            "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
            "code": class_code,
            "display": class_display,
        },
        "subject": {
            "reference": f"urn:uuid:{patient_uuid}",
        },
        "period": {
            "start": period_start,
            "end": period_end,
        },
    }


def generate_procedure(
    proc_uuid: str,
    patient_uuid: str,
    snomed_code: str,
    display: str,
    performed_date: str,
) -> dict:
    """Generate a single FHIR Procedure resource."""
    return {
        "resourceType": "Procedure",
        "status": "completed",
        "code": {
            "coding": [
                {
                    "system": "http://snomed.info/sct",
                    "code": snomed_code,
                    "display": display,
                }
            ],
            "text": display,
        },
        "subject": {
            "reference": f"urn:uuid:{patient_uuid}",
        },
        "performedDateTime": performed_date,
    }


def generate_allergy_intolerance(
    allergy_uuid: str,
    patient_uuid: str,
    snomed_code: str,
    display: str,
    category: str,
    recorded_date: str,
) -> dict:
    """Generate a single FHIR AllergyIntolerance resource."""
    return {
        "resourceType": "AllergyIntolerance",
        "clinicalStatus": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical",
                    "code": "active",
                }
            ]
        },
        "verificationStatus": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-verification",
                    "code": "confirmed",
                }
            ]
        },
        "type": "allergy",
        "category": [category],
        "code": {
            "coding": [
                {
                    "system": "http://snomed.info/sct",
                    "code": snomed_code,
                    "display": display,
                }
            ],
            "text": display,
        },
        "patient": {
            "reference": f"urn:uuid:{patient_uuid}",
        },
        "recordedDate": recorded_date,
    }


def generate_immunization(
    imm_uuid: str,
    patient_uuid: str,
    cvx_code: str,
    display: str,
    occurrence_date: str,
) -> dict:
    """Generate a single FHIR Immunization resource."""
    return {
        "resourceType": "Immunization",
        "status": "completed",
        "vaccineCode": {
            "coding": [
                {
                    "system": "http://hl7.org/fhir/sid/cvx",
                    "code": cvx_code,
                    "display": display,
                }
            ],
            "text": display,
        },
        "patient": {
            "reference": f"urn:uuid:{patient_uuid}",
        },
        "occurrenceDateTime": occurrence_date,
    }


def generate_diagnostic_report(
    report_uuid: str,
    patient_uuid: str,
    loinc_code: str,
    display: str,
    effective_date: str,
    observation_refs: list[str],
) -> dict:
    """Generate a single FHIR DiagnosticReport resource."""
    report = {
        "resourceType": "DiagnosticReport",
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/v2-0074",
                        "code": "LAB",
                        "display": "Laboratory",
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": loinc_code,
                    "display": display,
                }
            ],
            "text": display,
        },
        "subject": {
            "reference": f"urn:uuid:{patient_uuid}",
        },
        "effectiveDateTime": effective_date,
        "issued": f"{effective_date}T12:00:00Z",
    }
    if observation_refs:
        report["result"] = [{"reference": ref} for ref in observation_refs]
    return report


def generate_careplan(
    careplan_uuid: str,
    patient_uuid: str,
    title: str,
    status: str,
    intent: str,
    created_date: str,
    category_code: str,
    category_display: str,
    condition_uuids: list[str],
) -> dict:
    """Generate a single FHIR CarePlan resource."""
    careplan: dict = {
        "resourceType": "CarePlan",
        "status": status,
        "intent": intent,
        "title": title,
        "category": [
            {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": category_code,
                        "display": category_display,
                    }
                ]
            }
        ],
        "subject": {
            "reference": f"urn:uuid:{patient_uuid}",
        },
        "created": created_date,
    }
    if condition_uuids:
        careplan["addresses"] = [
            {"reference": f"urn:uuid:{cond_uuid}"} for cond_uuid in condition_uuids
        ]
    return careplan


def _make_entry(resource_uuid: str, resource: dict, resource_type: str) -> dict:
    """Create a bundle entry for a FHIR resource."""
    return {
        "fullUrl": f"urn:uuid:{resource_uuid}",
        "resource": resource,
        "request": {
            "method": "POST",
            "url": resource_type,
        },
    }


def generate_bundle(num_patients: int = 200) -> dict:
    """Generate a FHIR Transaction Bundle with patients, conditions,
    observations, medication requests, encounters, procedures,
    allergy intolerances, immunizations, diagnostic reports, and care plans."""
    entries: list[dict] = []
    # (uuid, birth_date, gender)
    all_patients: list[tuple[str, str, str]] = []
    patient_conditions: dict[str, set[str]] = {}  # uuid -> set of SNOMED codes
    # Track condition UUIDs per patient for CarePlan.addresses references
    # Maps patient_uuid -> list of (condition_uuid, snomed_code)
    patient_condition_refs: dict[str, list[tuple[str, str]]] = {}
    # Track observation UUIDs per patient for DiagnosticReport references
    patient_obs: dict[str, list[tuple[str, str]]] = {}  # uuid -> [(obs_uuid, loinc)]

    # --- Generate patients ---
    for _ in range(num_patients):
        patient_uuid = str(uuid.uuid4())
        patient = generate_patient(patient_uuid)
        all_patients.append((patient_uuid, patient["birthDate"], patient["gender"]))
        patient_conditions[patient_uuid] = set()
        patient_condition_refs[patient_uuid] = []
        patient_obs[patient_uuid] = []

        entries.append(_make_entry(patient_uuid, patient, "Patient"))

    # --- Guarantee: ≥5 patients >60y in Buenos Aires with diabetes ---
    reference_date = date(2025, 1, 1)
    guaranteed_count = 0
    diabetes_code = "44054006"
    diabetes_display = "Diabetes mellitus tipo 2"

    for patient_uuid, birth_date_str, _gender in all_patients:
        if guaranteed_count >= 7:
            break

        birth = date.fromisoformat(birth_date_str)
        age = (reference_date - birth).days // 365

        # Find the entry to check province
        entry = next(e for e in entries if e["fullUrl"] == f"urn:uuid:{patient_uuid}")
        patient_resource = entry["resource"]
        province = patient_resource["address"][0]["state"]

        if age > 60 and province == "Buenos Aires":
            cond_uuid = str(uuid.uuid4())
            condition = generate_condition(
                cond_uuid,
                patient_uuid,
                birth_date_str,
                diabetes_code,
                diabetes_display,
            )
            entries.append(_make_entry(cond_uuid, condition, "Condition"))
            patient_conditions[patient_uuid].add(diabetes_code)
            patient_condition_refs[patient_uuid].append((cond_uuid, diabetes_code))
            guaranteed_count += 1

    # --- Generate random conditions for remaining patients ---
    for patient_uuid, birth_date_str, _gender in all_patients:
        # Each patient gets 0-3 conditions
        num_conditions = random.choices([0, 1, 2, 3], weights=[0.15, 0.40, 0.30, 0.15], k=1)[0]
        for _ in range(num_conditions):
            condition_info = _weighted_choice(CONDITIONS)
            snomed_code, display_es, _, _ = condition_info
            cond_uuid = str(uuid.uuid4())
            condition = generate_condition(
                cond_uuid,
                patient_uuid,
                birth_date_str,
                snomed_code,
                display_es,
            )
            entries.append(_make_entry(cond_uuid, condition, "Condition"))
            patient_conditions[patient_uuid].add(snomed_code)
            patient_condition_refs[patient_uuid].append((cond_uuid, snomed_code))

    # ===================================================================
    # RESOURCES (after Patient+Condition)
    # ===================================================================

    # --- Generate observations ---
    obs_count = 0
    for patient_uuid, _birth_date_str, _gender in all_patients:
        patient_conds = patient_conditions.get(patient_uuid, set())
        # Each patient gets 3-6 observation types
        num_obs = random.randint(3, 6)
        selected_obs = random.sample(OBSERVATION_TYPES, k=min(num_obs, len(OBSERVATION_TYPES)))

        for obs_type in selected_obs:
            loinc_code, display, unit, n_lo, n_hi, a_lo, a_hi, related_snomed = obs_type
            # Use abnormal range if patient has the related condition
            if related_snomed and related_snomed in patient_conds:
                value = random.uniform(a_lo, a_hi)
            else:
                value = random.uniform(n_lo, n_hi)

            effective_date = _random_recent_date(years_back=2)
            obs_uuid = str(uuid.uuid4())
            observation = generate_observation(
                obs_uuid,
                patient_uuid,
                loinc_code,
                display,
                value,
                unit,
                effective_date,
            )
            entries.append(_make_entry(obs_uuid, observation, "Observation"))
            patient_obs[patient_uuid].append((obs_uuid, loinc_code))
            obs_count += 1

    # --- Generate medication requests ---
    med_count = 0
    for patient_uuid, _birth_date_str, _gender in all_patients:
        patient_conds = patient_conditions.get(patient_uuid, set())

        for atc_code, display, associated_snomeds in MEDICATIONS:
            should_prescribe = False
            if associated_snomeds:
                # Condition-specific: 70% chance if patient has the condition
                if any(s in patient_conds for s in associated_snomeds):
                    should_prescribe = random.random() < 0.70
            else:
                # General medication: 15% chance for anyone
                should_prescribe = random.random() < 0.15

            if should_prescribe:
                med_uuid = str(uuid.uuid4())
                status = random.choices(
                    ["active", "completed"],
                    weights=[0.85, 0.15],
                    k=1,
                )[0]
                authored = _random_recent_date(years_back=2)
                med_request = generate_medication_request(
                    med_uuid,
                    patient_uuid,
                    atc_code,
                    display,
                    status,
                    authored,
                )
                entries.append(_make_entry(med_uuid, med_request, "MedicationRequest"))
                med_count += 1

    # --- Generate encounters ---
    enc_count = 0
    for patient_uuid, _birth_date_str, _gender in all_patients:
        num_encounters = random.choices(
            [1, 2, 3, 4],
            weights=[0.30, 0.35, 0.25, 0.10],
            k=1,
        )[0]
        for _ in range(num_encounters):
            enc_type = _weighted_choice(ENCOUNTER_TYPES)
            class_code, class_display, _ = enc_type
            period_start = _random_recent_date(years_back=2)
            start_date = date.fromisoformat(period_start)

            # Duration depends on encounter type
            if class_code == "IMP":  # Internación: 2-14 days
                duration = random.randint(2, 14)
            elif class_code == "EMER":  # Guardia: 0-1 days
                duration = random.randint(0, 1)
            else:  # AMB, HH: same day
                duration = 0

            end_date = start_date + timedelta(days=duration)
            period_end = end_date.isoformat()

            enc_uuid = str(uuid.uuid4())
            encounter = generate_encounter(
                enc_uuid,
                patient_uuid,
                class_code,
                class_display,
                period_start,
                period_end,
            )
            entries.append(_make_entry(enc_uuid, encounter, "Encounter"))
            enc_count += 1

    # --- Generate procedures (Sprint 5.1) ---
    proc_count = 0
    for patient_uuid, _birth_date_str, gender in all_patients:
        patient_conds = patient_conditions.get(patient_uuid, set())
        # Each patient gets 0-2 procedures
        num_procs = random.choices([0, 1, 2], weights=[0.50, 0.35, 0.15], k=1)[0]
        for _ in range(num_procs):
            proc_info = _weighted_choice(PROCEDURES)
            snomed_code, display_es, required_conds, female_only, _ = proc_info
            # Skip female-only procedures for male patients
            if female_only and gender != "female":
                continue
            # Skip condition-specific procedures if patient lacks the condition
            if required_conds and not any(c in patient_conds for c in required_conds):
                continue
            proc_uuid = str(uuid.uuid4())
            performed = _random_recent_date(years_back=3)
            procedure = generate_procedure(
                proc_uuid,
                patient_uuid,
                snomed_code,
                display_es,
                performed,
            )
            entries.append(_make_entry(proc_uuid, procedure, "Procedure"))
            proc_count += 1

    # --- Generate allergy intolerances (Sprint 5.1) ---
    allergy_count = 0
    for patient_uuid, _birth_date_str, _gender in all_patients:
        # ~20% of patients have allergies
        if random.random() > 0.20:
            continue
        # Each allergic patient gets 1-2 allergies
        num_allergies = random.choices([1, 2], weights=[0.65, 0.35], k=1)[0]
        selected = random.sample(ALLERGIES, k=min(num_allergies, len(ALLERGIES)))
        for allergy_info in selected:
            snomed_code, display_es, category, _ = allergy_info
            allergy_uuid = str(uuid.uuid4())
            recorded = _random_recent_date(years_back=5)
            allergy = generate_allergy_intolerance(
                allergy_uuid,
                patient_uuid,
                snomed_code,
                display_es,
                category,
                recorded,
            )
            entries.append(_make_entry(allergy_uuid, allergy, "AllergyIntolerance"))
            allergy_count += 1

    # --- Generate immunizations (Sprint 5.1) ---
    imm_count = 0
    for patient_uuid, _birth_date_str, _gender in all_patients:
        # Each patient gets 2-5 vaccines
        num_vaccines = random.randint(2, 5)
        selected = random.sample(VACCINES, k=min(num_vaccines, len(VACCINES)))
        for vaccine_info in selected:
            cvx_code, display_es, _display_en, _ = vaccine_info
            imm_uuid = str(uuid.uuid4())
            occurrence = _random_recent_date(years_back=5)
            immunization = generate_immunization(
                imm_uuid,
                patient_uuid,
                cvx_code,
                display_es,
                occurrence,
            )
            entries.append(_make_entry(imm_uuid, immunization, "Immunization"))
            imm_count += 1

    # --- Generate diagnostic reports (Sprint 5.1) ---
    report_count = 0
    for patient_uuid, _birth_date_str, _gender in all_patients:
        # Each patient gets 0-2 diagnostic reports
        num_reports = random.choices([0, 1, 2], weights=[0.30, 0.45, 0.25], k=1)[0]
        if num_reports == 0:
            continue
        selected = random.sample(
            DIAGNOSTIC_REPORT_TYPES,
            k=min(num_reports, len(DIAGNOSTIC_REPORT_TYPES)),
        )
        for report_info in selected:
            loinc_code, display_es, _display_en, component_loincs, _ = report_info
            report_uuid = str(uuid.uuid4())
            effective = _random_recent_date(years_back=2)
            # Find matching observation UUIDs for this patient
            obs_refs = [
                f"urn:uuid:{obs_id}"
                for obs_id, obs_loinc in patient_obs.get(patient_uuid, [])
                if obs_loinc in component_loincs
            ]
            report = generate_diagnostic_report(
                report_uuid,
                patient_uuid,
                loinc_code,
                display_es,
                effective,
                obs_refs,
            )
            entries.append(_make_entry(report_uuid, report, "DiagnosticReport"))
            report_count += 1

    # --- Generate care plans (Sprint 5.3) ---
    careplan_count = 0
    careplan_active_count = 0
    for patient_uuid, _birth_date_str, _gender in all_patients:
        cond_refs = patient_condition_refs.get(patient_uuid, [])
        if not cond_refs:
            continue
        # ~55% of patients with conditions get a care plan
        if random.random() > 0.55:
            continue

        # Pick 1-2 conditions to address (prefer conditions with templates)
        num_addressed = min(random.choices([1, 2], weights=[0.7, 0.3], k=1)[0], len(cond_refs))
        # Sort: conditions with templates first
        sorted_refs = sorted(
            cond_refs,
            key=lambda x: x[1] in CAREPLAN_TEMPLATES,
            reverse=True,
        )
        addressed = sorted_refs[:num_addressed]

        # Use template from first addressed condition
        primary_snomed = addressed[0][1]
        title, cat_code, cat_display = CAREPLAN_TEMPLATES.get(primary_snomed, CAREPLAN_GENERIC)

        status, _ = _weighted_choice(CAREPLAN_STATUSES)
        created = _random_recent_date(years_back=2)
        careplan_uuid = str(uuid.uuid4())

        cp = generate_careplan(
            careplan_uuid,
            patient_uuid,
            title,
            status,
            "plan",
            created,
            cat_code,
            cat_display,
            [cond_uuid for cond_uuid, _ in addressed],
        )
        entries.append(_make_entry(careplan_uuid, cp, "CarePlan"))
        careplan_count += 1
        if status == "active":
            careplan_active_count += 1

    # --- Build bundle ---
    bundle = {
        "resourceType": "Bundle",
        "type": "transaction",
        "entry": entries,
    }

    # --- Stats ---
    num_conditions = sum(1 for e in entries if e["resource"]["resourceType"] == "Condition")
    print(f"Generated {num_patients} patients, {num_conditions} conditions, "
          f"{obs_count} observations, {med_count} medication requests, "
          f"{enc_count} encounters")
    print(f"  {proc_count} procedures, {allergy_count} allergy intolerances, "
          f"{imm_count} immunizations, {report_count} diagnostic reports")
    print(f"  {careplan_count} care plans ({careplan_active_count} active)")
    print(f"Guaranteed diabetes >60y Buenos Aires: {guaranteed_count}")
    print(f"Total bundle entries: {len(entries)}")

    return bundle


def main() -> None:
    """Generate and write the seed bundle to a JSON file."""
    default_path = Path(__file__).parent / "seed_bundle.json"
    output_path = Path(sys.argv[1]) if len(sys.argv) > 1 else default_path
    bundle = generate_bundle()
    output_path.write_text(json.dumps(bundle, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Written to {output_path}")


if __name__ == "__main__":
    main()
