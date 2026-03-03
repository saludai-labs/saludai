"""Generate synthetic FHIR R4 seed data with Argentine demographics.

Produces a Transaction Bundle with ~55 patients and ~100 conditions
using realistic Argentine names, DNI, provinces, and SNOMED CT codes.

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
    "Juan", "Carlos", "José", "Luis", "Miguel", "Jorge", "Pablo",
    "Diego", "Martín", "Alejandro", "Ricardo", "Fernando", "Daniel",
    "Sergio", "Roberto", "Eduardo", "Raúl", "Héctor", "Oscar", "Mario",
    "Gustavo", "Andrés", "Marcelo", "Nicolás", "Santiago", "Matías",
    "Facundo", "Leandro", "Tomás", "Agustín",
]

FIRST_NAMES_FEMALE = [
    "María", "Ana", "Laura", "Lucía", "Marta", "Silvia", "Patricia",
    "Claudia", "Gabriela", "Valentina", "Florencia", "Carolina",
    "Camila", "Julieta", "Sofía", "Victoria", "Romina", "Daniela",
    "Andrea", "Verónica", "Graciela", "Liliana", "Soledad", "Celeste",
    "Milagros", "Rocío", "Natalia", "Mariana", "Paula", "Eugenia",
]

LAST_NAMES = [
    "González", "Rodríguez", "Gómez", "Fernández", "López", "Díaz",
    "Martínez", "Pérez", "García", "Sánchez", "Romero", "Sosa",
    "Álvarez", "Torres", "Ruiz", "Ramírez", "Flores", "Acosta",
    "Medina", "Benítez", "Herrera", "Suárez", "Aguirre", "Castro",
    "Ríos", "Ortiz", "Luna", "Juárez", "Cabrera", "Morales",
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

# SNOMED CT codes for conditions prevalent in Argentina
# (code, display_es, display_en, prevalence_weight)
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
    clinical_status = random.choices(
        ["active", "resolved"], weights=[0.8, 0.2], k=1
    )[0]

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


def generate_bundle(num_patients: int = 55) -> dict:
    """Generate a FHIR Transaction Bundle with patients and conditions."""
    entries: list[dict] = []
    all_patients: list[tuple[str, str]] = []  # (uuid, birth_date)

    # --- Generate patients ---
    for _ in range(num_patients):
        patient_uuid = str(uuid.uuid4())
        patient = generate_patient(patient_uuid)
        all_patients.append((patient_uuid, patient["birthDate"]))

        entries.append(
            {
                "fullUrl": f"urn:uuid:{patient_uuid}",
                "resource": patient,
                "request": {
                    "method": "POST",
                    "url": "Patient",
                },
            }
        )

    # --- Guarantee: ≥5 patients >60y in Buenos Aires with diabetes ---
    reference_date = date(2025, 1, 1)
    guaranteed_count = 0
    diabetes_code = "44054006"
    diabetes_display = "Diabetes mellitus tipo 2"

    for patient_uuid, birth_date_str in all_patients:
        if guaranteed_count >= 7:
            break

        birth = date.fromisoformat(birth_date_str)
        age = (reference_date - birth).days // 365

        # Find the entry to check province
        entry = next(
            e
            for e in entries
            if e["fullUrl"] == f"urn:uuid:{patient_uuid}"
        )
        patient_resource = entry["resource"]
        province = patient_resource["address"][0]["state"]

        if age > 60 and province == "Buenos Aires":
            cond_uuid = str(uuid.uuid4())
            condition = generate_condition(
                cond_uuid, patient_uuid, birth_date_str,
                diabetes_code, diabetes_display,
            )
            entries.append(
                {
                    "fullUrl": f"urn:uuid:{cond_uuid}",
                    "resource": condition,
                    "request": {
                        "method": "POST",
                        "url": "Condition",
                    },
                }
            )
            guaranteed_count += 1

    # --- Generate random conditions for remaining patients ---
    conditions_generated = guaranteed_count
    for patient_uuid, birth_date_str in all_patients:
        # Each patient gets 0-3 conditions
        num_conditions = random.choices([0, 1, 2, 3], weights=[0.15, 0.40, 0.30, 0.15], k=1)[0]
        for _ in range(num_conditions):
            condition_info = _weighted_choice(CONDITIONS)
            snomed_code, display_es, _, _ = condition_info
            cond_uuid = str(uuid.uuid4())
            condition = generate_condition(
                cond_uuid, patient_uuid, birth_date_str,
                snomed_code, display_es,
            )
            entries.append(
                {
                    "fullUrl": f"urn:uuid:{cond_uuid}",
                    "resource": condition,
                    "request": {
                        "method": "POST",
                        "url": "Condition",
                    },
                }
            )
            conditions_generated += 1

    # --- Build bundle ---
    bundle = {
        "resourceType": "Bundle",
        "type": "transaction",
        "entry": entries,
    }

    # --- Stats ---
    num_conditions = sum(
        1 for e in entries if e["resource"]["resourceType"] == "Condition"
    )
    print(f"Generated {num_patients} patients and {num_conditions} conditions")
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
