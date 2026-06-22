# src/retrieval/query_understanding.py  (v3)
#
# Fixes vs v2:
#   1. ENTITY_MAP now covers ALL node types in the graph, not just
#      Symptom/FailureMode. Cause, Mitigation, Parameter, OperatingFactor,
#      and Method nodes (62 of 111 total graph nodes) were previously
#      invisible to the router, so any question naming a specific cause
#      or mitigation (e.g. "take-off derate") fell through to noisy term
#      search instead of a precise entity match / path traversal.
#   2. Removed the blind "egt" -> "egt margin" expansion. Any question
#      mentioning EGT anywhere was dragging in FM_egt_margin_deterioration
#      as a matched entity even when irrelevant (e.g. an acute flameout
#      scenario that happens to mention EGT decaying), polluting context
#      with unrelated chronic-deterioration chunks.
#   3. Expanded STOPWORDS with question-instruction / provenance-meta
#      words ("identify", "explain", "document", "page", "claim", etc.)
#      that were being forwarded as graph-search keywords and adding
#      noise to the term-based retrieval fallback.
#
# Interface is unchanged: QueryRouter().understand(query) -> QueryUnderstanding
# with the same fields. Existing callers (graph_rag_v1.py, run_eval.py,
# Ragas_eval_groq_stable.py) work without modification.

from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class QueryUnderstanding:
    query: str
    intent: str
    entity_id: Optional[str]
    entity_name: Optional[str]
    entity_type: Optional[str]
    retrieval_method: str

    keywords: List[str] = field(default_factory=list)
    expanded_terms: List[str] = field(default_factory=list)
    matched_entities: List[Dict[str, Any]] = field(default_factory=list)
    retrieval_plan: Dict[str, Any] = field(default_factory=dict)


class QueryRouter:
    """
    Deterministic, recall-heavy query understanding for AeroOps GraphRAG.
    """

    PLAN_PREFIX = "PLAN::"

    # Phrase/entity map. Grounded in the actual 111 nodes in the cleaned
    # AeroOps graph (aeroops_kg_cleaned.json). Add aliases here as the
    # graph grows -- but only for ids that actually exist in the graph.
    ENTITY_MAP: Dict[str, Tuple[str, str, str]] = {
        # ---------------- Symptoms ----------------
        "high egt": ("SY_high_egt", "High / rising EGT", "Symptom"),
        "rising egt": ("SY_high_egt", "High / rising EGT", "Symptom"),
        "egt rise": ("SY_high_egt", "High / rising EGT", "Symptom"),
        "egt rising": ("SY_high_egt", "High / rising EGT", "Symptom"),
        "temperature rising": ("SY_high_egt", "High / rising EGT", "Symptom"),
        "exhaust gas temperature": ("SY_high_egt", "High / rising EGT", "Symptom"),
        "egt exceedance": ("SY_egt_exceedance", "EGT redline exceedance", "Symptom"),
        "egt redline": ("SY_egt_exceedance", "EGT redline exceedance", "Symptom"),
        "low epr": ("SY_low_epr", "Low EPR", "Symptom"),
        "epr fluctuation": ("SY_epr_fluctuation", "Rapid EPR fluctuation", "Symptom"),
        "rapid epr": ("SY_epr_fluctuation", "Rapid EPR fluctuation", "Symptom"),
        "low n1": ("SY_low_n1", "Low N1", "Symptom"),
        "n1 fluctuation": ("SY_n1_fluctuation", "Fluctuating N1", "Symptom"),
        "fluctuating n1": ("SY_n1_fluctuation", "Fluctuating N1", "Symptom"),
        "loud bang": ("SY_loud_bang", "Loud bang and yaw", "Symptom"),
        "high vibration": ("SY_high_vibration", "High vibration", "Symptom"),
        "vibration": ("SY_high_vibration", "High vibration", "Symptom"),
        "shaking": ("SY_high_vibration", "High vibration", "Symptom"),
        "visible flame": ("SY_visible_flame", "Visible flame from inlet / tailpipe", "Symptom"),
        "rising fuel flow": ("SY_rising_fuel_flow", "Rising fuel flow", "Symptom"),
        "high fuel flow": ("SY_high_fuel_flow", "Abnormally high fuel flow", "Symptom"),
        "low oil pressure": ("SY_low_oil_pressure", "Low oil pressure", "Symptom"),
        "high oil temperature": ("SY_high_oil_temp", "High oil temperature", "Symptom"),
        "oil temperature rising": ("SY_high_oil_temp", "High oil temperature", "Symptom"),
        "oil quantity": ("SY_decreasing_oil_quantity", "Steady decrease in oil quantity", "Symptom"),
        "oil loss": ("SY_decreasing_oil_quantity", "Steady decrease in oil quantity", "Symptom"),
        "decreasing oil quantity": ("SY_decreasing_oil_quantity", "Steady decrease in oil quantity", "Symptom"),
        "oil filter bypass": ("SY_oil_filter_bypass", "Oil filter bypass indication", "Symptom"),
        "fire warning": ("SY_fire_warning", "Fire warning", "Symptom"),
        "sfc increase": ("SY_sfc_increase", "Cruise SFC increase / higher fuel burn", "Symptom"),
        "fuel burn increase": ("SY_sfc_increase", "Cruise SFC increase / higher fuel burn", "Symptom"),
        "higher fuel burn": ("SY_sfc_increase", "Cruise SFC increase / higher fuel burn", "Symptom"),

        # ---------------- Failure modes ----------------
        "compressor surge": ("FM_compressor_surge", "Compressor surge / stall", "FailureMode"),
        "compressor stall": ("FM_compressor_surge", "Compressor surge / stall", "FailureMode"),
        "surge": ("FM_compressor_surge", "Compressor surge / stall", "FailureMode"),
        "flameout": ("FM_flameout", "Flameout", "FailureMode"),
        "bearing failure": ("FM_bearing_failure", "Bearing failure", "FailureMode"),
        "oil leak": ("FM_oil_leak_or_oil_loss", "Oil leak / oil loss", "FailureMode"),
        "tailpipe fire": ("FM_tailpipe_fire", "Tailpipe fire", "FailureMode"),
        "engine fire": ("FM_engine_fire", "Engine fire", "FailureMode"),
        "hot start": ("FM_hot_start", "Hot start", "FailureMode"),
        "fod": ("FM_fod", "Foreign Object Damage", "FailureMode"),
        "foreign object damage": ("FM_fod", "Foreign Object Damage", "FailureMode"),
        "foreign object ingestion": ("FM_fod", "Foreign Object Damage", "FailureMode"),
        "object ingestion": ("FM_fod", "Foreign Object Damage", "FailureMode"),
        "bird ingestion": ("FM_fod", "Foreign Object Damage", "FailureMode"),
        "bird strike": ("FM_fod", "Foreign Object Damage", "FailureMode"),
        "birds": ("FM_fod", "Foreign Object Damage", "FailureMode"),
        "bird": ("FM_fod", "Foreign Object Damage", "FailureMode"),
        "flock of birds": ("FM_fod", "Foreign Object Damage", "FailureMode"),
        "egt margin deterioration": ("FM_egt_margin_deterioration", "EGT margin deterioration", "FailureMode"),
        "egt margin": ("FM_egt_margin_deterioration", "EGT margin deterioration", "FailureMode"),
        "tip clearance": ("FM_tip_clearance_increase", "Blade-tip clearance increase", "FailureMode"),
        "blade-tip clearance": ("FM_tip_clearance_increase", "Blade-tip clearance increase", "FailureMode"),
        "blade tip rub": ("FM_blade_tip_rub", "Blade tip rub", "FailureMode"),
        "tip rub": ("FM_blade_tip_rub", "Blade tip rub", "FailureMode"),
        "airfoil erosion": ("FM_airfoil_erosion", "Airfoil erosion / surface roughness", "FailureMode"),
        "blade erosion": ("FM_airfoil_erosion", "Airfoil erosion / surface roughness", "FailureMode"),
        "surface roughness": ("FM_airfoil_erosion", "Airfoil erosion / surface roughness", "FailureMode"),
        "thermal distortion": ("FM_thermal_distortion", "Thermal distortion / vane warpage", "FailureMode"),
        "vane warpage": ("FM_thermal_distortion", "Thermal distortion / vane warpage", "FailureMode"),
        "hardware deterioration": ("FM_hardware_deterioration", "Hardware deterioration / blade distress", "FailureMode"),
        "blade distress": ("FM_hardware_deterioration", "Hardware deterioration / blade distress", "FailureMode"),
        "llp expiry": ("FM_llp_expiry", "Life-Limited Part (LLP) expiry", "FailureMode"),
        "life-limited part": ("FM_llp_expiry", "Life-Limited Part (LLP) expiry", "FailureMode"),
        "life limited part": ("FM_llp_expiry", "Life-Limited Part (LLP) expiry", "FailureMode"),
        "severe engine damage": ("FM_severe_engine_damage", "Severe engine damage", "FailureMode"),
        "blade cracking": ("FM_blade_cracking", "Blade cracking / chipping", "FailureMode"),
        "blade chipping": ("FM_blade_cracking", "Blade cracking / chipping", "FailureMode"),
        "corrosion": ("FM_corrosion", "Corrosion / oxidation", "FailureMode"),
        "oxidation": ("FM_corrosion", "Corrosion / oxidation", "FailureMode"),
        "blocked cooling holes": ("FM_blocked_cooling_holes", "Blocked HPT cooling holes", "FailureMode"),
        "cooling hole blockage": ("FM_blocked_cooling_holes", "Blocked HPT cooling holes", "FailureMode"),
        "fuel filter clogging": ("FM_fuel_filter_clogging", "Fuel filter clogging", "FailureMode"),
        "fuel filter": ("FM_fuel_filter_clogging", "Fuel filter clogging", "FailureMode"),
        "fan unbalance": ("FM_fan_unbalance", "Fan unbalance", "FailureMode"),
        "fan imbalance": ("FM_fan_unbalance", "Fan unbalance", "FailureMode"),

        # ---------------- Causes ----------------
        "particulate ingestion": ("C_particulate_ingestion", "Particulate / dust / sand ingestion", "Cause"),
        "dust ingestion": ("C_particulate_ingestion", "Particulate / dust / sand ingestion", "Cause"),
        "sand ingestion": ("C_particulate_ingestion", "Particulate / dust / sand ingestion", "Cause"),
        "thermal stress": ("C_thermal_stress", "Thermal stress / high core temperature", "Cause"),
        "blade tip wear": ("C_blade_tip_wear", "Blade tip wear", "Cause"),
        "tip wear": ("C_blade_tip_wear", "Blade tip wear", "Cause"),
        "flight loads": ("C_flight_loads", "Flight loads (aerodynamic + inertial)", "Cause"),
        "hot rotor reburst": ("C_hot_rotor_reburst", "Hot rotor reburst (thermal transient)", "Cause"),
        "rotor reburst": ("C_hot_rotor_reburst", "Hot rotor reburst (thermal transient)", "Cause"),
        "rotor case interference": ("C_rotor_case_interference", "Rotor / case interference", "Cause"),
        "rotor/case interference": ("C_rotor_case_interference", "Rotor / case interference", "Cause"),
        "case interference": ("C_rotor_case_interference", "Rotor / case interference", "Cause"),
        "compressor airfoil stall": ("C_compressor_airfoil_stall", "Compressor airfoil aerodynamic stall", "Cause"),
        "airfoil stall": ("C_compressor_airfoil_stall", "Compressor airfoil aerodynamic stall", "Cause"),
        "fuel starvation": ("C_fuel_starvation", "Fuel starvation / interruption", "Cause"),
        "fuel interruption": ("C_fuel_starvation", "Fuel starvation / interruption", "Cause"),
        "bearing distress": ("C_bearing_distress", "Bearing distress", "Cause"),
        "combustion heat": ("C_combustion_heat", "Combustion heat / oxidation", "Cause"),
        "fuel puddling": ("C_fuel_puddling", "Fuel puddling in tailpipe", "Cause"),
        "boost pump failure": ("C_boost_pump_failure", "Fuel boost-pump debris", "Cause"),
        "boost pump debris": ("C_boost_pump_failure", "Fuel boost-pump debris", "Cause"),

        # ---------------- Mitigations ----------------
        "water wash": ("MI_water_wash", "Engine water washing", "Mitigation"),
        "water washing": ("MI_water_wash", "Engine water washing", "Mitigation"),
        "engine wash": ("MI_water_wash", "Engine water washing", "Mitigation"),
        "take-off derate": ("MI_takeoff_derate", "Take-off derate", "Mitigation"),
        "take off derate": ("MI_takeoff_derate", "Take-off derate", "Mitigation"),
        "takeoff derate": ("MI_takeoff_derate", "Take-off derate", "Mitigation"),
        "derate": ("MI_takeoff_derate", "Take-off derate", "Mitigation"),
        "performance restoration": ("MI_performance_restoration", "Performance restoration shop visit", "Mitigation"),
        "llp replacement": ("MI_llp_replacement", "LLP replacement", "Mitigation"),
        "borescope": ("MI_borescope_inspection", "Borescope inspection", "Mitigation"),
        "borescope inspection": ("MI_borescope_inspection", "Borescope inspection", "Mitigation"),
        "on-condition monitoring": ("MI_on_condition_monitoring", "On-condition / trend monitoring", "Mitigation"),
        "trend monitoring": ("MI_on_condition_monitoring", "On-condition / trend monitoring", "Mitigation"),
        "condition monitoring": ("MI_on_condition_monitoring", "On-condition / trend monitoring", "Mitigation"),
        "engine overhaul": ("MI_overhaul", "Engine overhaul / full teardown", "Mitigation"),
        "overhaul": ("MI_overhaul", "Engine overhaul / full teardown", "Mitigation"),
        "non-destructive testing": ("MI_ndt", "Non-destructive testing (NDT) inspection", "Mitigation"),
        "non destructive testing": ("MI_ndt", "Non-destructive testing (NDT) inspection", "Mitigation"),
        "ndt": ("MI_ndt", "Non-destructive testing (NDT) inspection", "Mitigation"),
        "thrust reduction": ("MI_thrust_reduction", "Thrust reduction (retard thrust lever)", "Mitigation"),
        "retard thrust lever": ("MI_thrust_reduction", "Thrust reduction (retard thrust lever)", "Mitigation"),
        "retard the thrust lever": ("MI_thrust_reduction", "Thrust reduction (retard thrust lever)", "Mitigation"),
        "engine shutdown": ("MI_engine_shutdown", "Engine shutdown", "Mitigation"),
        "continuous ignition": ("MI_continuous_ignition", "Continuous ignition", "Mitigation"),
        "active clearance control": ("MI_clearance_control_bleed", "Active clearance control (case cooling bleed)", "Mitigation"),
        "clearance control": ("MI_clearance_control_bleed", "Active clearance control (case cooling bleed)", "Mitigation"),
        "case cooling bleed": ("MI_clearance_control_bleed", "Active clearance control (case cooling bleed)", "Mitigation"),
        "predictive maintenance": ("MI_predictive_maintenance", "Predictive maintenance (RUL / PHM)", "Mitigation"),
        "dry motoring": ("MI_dry_motoring", "Dry motoring the engine", "Mitigation"),
        "dry motor": ("MI_dry_motoring", "Dry motoring the engine", "Mitigation"),

        # ---------------- Parameters ----------------
        "sfc": ("PA_sfc", "Specific Fuel Consumption (SFC)", "Parameter"),
        "specific fuel consumption": ("PA_sfc", "Specific Fuel Consumption (SFC)", "Parameter"),
        "fan speed": ("PA_n1", "N1 fan speed", "Parameter"),
        "fuel flow": ("PA_fuel_flow", "Fuel flow", "Parameter"),
        "oil pressure": ("PA_oil_pressure", "Oil pressure", "Parameter"),

        # ---------------- Operating factors ----------------
        "flight length": ("OF_flight_length", "Flight length / sector length", "OperatingFactor"),
        "sector length": ("OF_flight_length", "Flight length / sector length", "OperatingFactor"),
        "stage length": ("OF_flight_length", "Flight length / sector length", "OperatingFactor"),
        "outside air temperature": ("OF_oat", "Outside air temperature (OAT)", "OperatingFactor"),
        "ambient temperature": ("OF_oat", "Outside air temperature (OAT)", "OperatingFactor"),
        "operating environment": ("OF_environment", "Operating environment (dusty / erosive / temperate)", "OperatingFactor"),
        "dusty environment": ("OF_environment", "Operating environment (dusty / erosive / temperate)", "OperatingFactor"),
        "erosive environment": ("OF_environment", "Operating environment (dusty / erosive / temperate)", "OperatingFactor"),
        "thrust rating": ("OF_thrust_rating", "Thrust rating", "OperatingFactor"),
        "engine age": ("OF_engine_age", "Engine age / phase (first-run vs mature)", "OperatingFactor"),
        "short-haul": ("OF_short_haul", "Short-haul / high-cycle operation", "OperatingFactor"),
        "short haul": ("OF_short_haul", "Short-haul / high-cycle operation", "OperatingFactor"),
        "high-cycle operation": ("OF_short_haul", "Short-haul / high-cycle operation", "OperatingFactor"),
        "high cycle operation": ("OF_short_haul", "Short-haul / high-cycle operation", "OperatingFactor"),

        # ---------------- Methods ----------------
        "prognostics and health management": ("ME_phm", "Prognostics & Health Management (PHM)", "Method"),
        "phm": ("ME_phm", "Prognostics & Health Management (PHM)", "Method"),
        "ann-flux": ("ME_ann_flux", "ANN-Flux (custom-loss neural network)", "Method"),
        "ann flux": ("ME_ann_flux", "ANN-Flux (custom-loss neural network)", "Method"),
        "pca orthogonalization": ("ME_pca", "PCA orthogonalization", "Method"),
        "pca": ("ME_pca", "PCA orthogonalization", "Method"),
        "symbolic regression": ("ME_symbolic_regression", "Symbolic regression (EGT modeling)", "Method"),
        "fadec": ("ME_fadec", "FADEC / EEC engine control", "Method"),
        "eec": ("ME_fadec", "FADEC / EEC engine control", "Method"),
        "n-cmapss": ("ME_ncmapss", "N-CMAPSS run-to-failure dataset", "Method"),
        "ncmapss": ("ME_ncmapss", "N-CMAPSS run-to-failure dataset", "Method"),
        "cmapss": ("ME_ncmapss", "N-CMAPSS run-to-failure dataset", "Method"),
    }

    # Domain term expansion. Intentionally recall-heavy, BUT kept narrow
    # enough that a single generic word doesn't drag in an unrelated
    # failure mode. The previous "egt" -> [..., "egt margin"] expansion
    # was removed: it caused FM_egt_margin_deterioration (a chronic
    # degradation failure mode) to match on ANY question mentioning EGT,
    # including acute-event scenarios where it's irrelevant (e.g. a
    # flameout scenario that happens to mention EGT decaying).
    TERM_EXPANSIONS: Dict[str, List[str]] = {
        "bird": ["birds", "bird strike", "bird ingestion", "foreign object ingestion", "foreign object damage", "fod", "engine ingestion"],
        "birds": ["bird", "bird strike", "bird ingestion", "foreign object ingestion", "foreign object damage", "fod", "engine ingestion"],
        "flock": ["birds", "bird ingestion", "bird strike", "fod"],
        "flew into": ["ingestion", "foreign object ingestion", "fod"],
        "ingestion": ["foreign object ingestion", "fod", "foreign object damage"],
        "debris": ["foreign object", "foreign object damage", "fod"],
        "object": ["foreign object", "foreign object damage", "fod"],
        "smoke": ["fire warning", "engine fire", "tailpipe fire"],
        "fire": ["fire warning", "engine fire", "tailpipe fire"],
        "temperature": ["egt", "high egt", "exhaust gas temperature"],
        # NOTE: "egt margin" intentionally removed from this list (see
        # module docstring). "egt" alone now only expands to symptom-level
        # aliases, not the chronic-deterioration failure mode.
        "egt": ["high egt", "rising egt", "egt exceedance"],
        "shake": ["vibration", "high vibration"],
        "shaking": ["vibration", "high vibration"],
        "vibrating": ["vibration", "high vibration"],
        "power loss": ["low epr", "flameout", "compressor surge"],
        "thrust loss": ["low epr", "flameout", "compressor surge"],
        "oil": ["oil pressure", "oil temperature"],
        "surge": ["compressor surge", "compressor stall"],
        "stall": ["compressor stall", "compressor surge"],
        "derate": ["take-off derate", "takeoff derate"],
        "wash": ["water wash", "water washing", "engine wash"],
    }

    STOPWORDS = {
        "a", "an", "and", "are", "as", "at", "be", "by", "can", "could", "did", "do",
        "does", "for", "from", "had", "has", "have", "how", "i", "if", "in", "into",
        "is", "it", "of", "on", "or", "our", "should", "that", "the", "there", "this",
        "to", "was", "we", "what", "when", "where", "which", "with", "would", "you",

        # Question-instruction / meta words. These appear constantly in
        # eval question phrasing ("identify", "explain", "trace the
        # sequence") but carry no graph-entity signal. Forwarding them as
        # keywords to the term-based retriever fallback was injecting
        # noise -- generic words can fuzzy-match many unrelated node
        # names via CONTAINS-based matching in the graph query.
        "identify", "explain", "describe", "give", "name", "state", "list",
        "sequence", "connects", "connecting", "trace", "summarize", "discuss",
        "compare", "consider", "regarding", "according",

        # Provenance / citation meta words (Q24-26 style "what's the
        # source for this claim" questions repeatedly leaked these as
        # keywords, polluting term search with no entity value).
        "claim", "claims", "document", "documents", "page", "pages",
        "wording", "source", "sources", "supporting", "supports", "support",
        "evidence", "mention", "mentions", "mentioned", "documented",
        "cite", "citation", "citations",

        # Generic engine/domain filler that matches too many node names
        # via fuzzy CONTAINS search without adding entity-identifying
        # signal (e.g. "engine" matches "Turbofan engine", "High-bypass
        # ratio turbofan", etc. almost regardless of question intent).
        "engine", "engines", "rate", "rates", "effect", "affects",
    }

    def understand(self, query: str) -> QueryUnderstanding:
        q = self._normalize(query)

        keywords = self._extract_keywords(q)
        expanded_terms = self._expand_terms(q, keywords)
        matched_entities = self._match_entities(q, expanded_terms)
        intent = self._infer_intent(q)
        retrieval_plan = self._build_retrieval_plan(query, intent, keywords, expanded_terms, matched_entities)

        primary = matched_entities[0] if matched_entities else None

        if primary and len(matched_entities) == 1 and len(expanded_terms) <= 3:
            entity_id = primary["id"]
            retrieval_method = self._select_retrieval_method(primary["type"])
        else:
            entity_id = self.encode_plan(retrieval_plan)
            retrieval_method = "retrieve_by_query_plan"

        return QueryUnderstanding(
            query=query,
            intent=intent,
            entity_id=entity_id,
            entity_name=primary["name"] if primary else None,
            entity_type=primary["type"] if primary else None,
            retrieval_method=retrieval_method,
            keywords=keywords,
            expanded_terms=expanded_terms,
            matched_entities=matched_entities,
            retrieval_plan=retrieval_plan,
        )

    @classmethod
    def encode_plan(cls, plan: Dict[str, Any]) -> str:
        raw = json.dumps(plan, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return cls.PLAN_PREFIX + base64.urlsafe_b64encode(raw).decode("ascii")

    @classmethod
    def decode_plan(cls, encoded: str) -> Dict[str, Any]:
        if not encoded.startswith(cls.PLAN_PREFIX):
            raise ValueError("Not an encoded AeroOps retrieval plan.")
        raw = base64.urlsafe_b64decode(encoded[len(cls.PLAN_PREFIX):].encode("ascii"))
        return json.loads(raw.decode("utf-8"))

    def _normalize(self, query: str) -> str:
        q = query.lower().strip()
        # Hyphens -> spaces BEFORE the character filter. Source text uses
        # hyphenated compounds inconsistently ("oil-pressure" vs "oil
        # pressure", "take-off" vs "take off"). Without this, a query
        # written with a hyphen silently fails to match ENTITY_MAP keys
        # written with a space (e.g. "low oil-pressure caption" never
        # matched "low oil pressure" -> SY_low_oil_pressure).
        q = q.replace("-", " ")
        q = re.sub(r"[^a-z0-9/+\.\s]", " ", q)
        q = re.sub(r"\s+", " ", q)
        return q

    def _extract_keywords(self, q: str) -> List[str]:
        terms: List[str] = []

        for phrase in sorted(self.ENTITY_MAP.keys(), key=len, reverse=True):
            if phrase in q:
                terms.append(phrase)

        for phrase in sorted(self.TERM_EXPANSIONS.keys(), key=len, reverse=True):
            if phrase in q:
                terms.append(phrase)

        tokens = re.findall(r"[a-z0-9/+\-\.]+", q)
        for token in tokens:
            if token in self.STOPWORDS or len(token) < 3:
                continue
            if any(token in existing for existing in terms):
                continue
            terms.append(token)

        return self._dedupe(terms)

    def _expand_terms(self, q: str, keywords: List[str]) -> List[str]:
        expanded: List[str] = list(keywords)

        for term in keywords:
            expanded.extend(self.TERM_EXPANSIONS.get(term, []))

        if "bird" in q or "birds" in q or "flock" in q:
            expanded.extend(["bird ingestion", "bird strike", "foreign object ingestion", "foreign object damage", "fod"])

        if "flew into" in q or "went into" in q or "entered" in q:
            expanded.extend(["ingestion", "foreign object ingestion", "fod"])

        if "what should" in q or "steps" in q or "action" in q:
            expanded.extend(["mitigation", "inspection", "maintenance action", "procedure"])

        return self._dedupe(expanded)

    def _match_entities(self, q: str, terms: List[str]) -> List[Dict[str, Any]]:
        matches: List[Dict[str, Any]] = []
        search_space = " ".join([q] + terms)

        for phrase, (entity_id, entity_name, entity_type) in sorted(self.ENTITY_MAP.items(), key=lambda x: len(x[0]), reverse=True):
            if phrase in search_space:
                matches.append({
                    "id": entity_id,
                    "name": entity_name,
                    "type": entity_type,
                    "matched_phrase": phrase,
                })

        seen = set()
        unique = []
        for match in matches:
            if match["id"] in seen:
                continue
            seen.add(match["id"])
            unique.append(match)
        return unique

    def _infer_intent(self, q: str) -> str:
        if any(phrase in q for phrase in ["what should", "what do we do", "steps", "next step", "check first", "inspect first"]):
            return "action_steps"

        if any(word in q for word in ["mitigate", "mitigation", "action", "handle", "fix", "tackle", "procedure"]):
            return "mitigation_lookup"

        if any(word in q for word in ["cause", "causes", "why", "trigger", "triggered"]):
            return "cause_lookup"

        if any(word in q for word in ["symptom", "symptoms", "indicate", "sign", "means", "suggest"]):
            return "diagnosis"

        if any(word in q for word in ["compare", "difference", "versus", "vs"]):
            return "comparison"

        if any(word in q for word in ["safe", "serious", "dispatch", "dispatchable", "ground", "shutdown"]):
            return "safety_escalation"

        return "general_graph_lookup"

    def _build_retrieval_plan(
        self,
        query: str,
        intent: str,
        keywords: List[str],
        expanded_terms: List[str],
        matched_entities: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        return {
            "query": query,
            "intent": intent,
            "keywords": keywords,
            "expanded_terms": expanded_terms,
            "matched_entities": matched_entities,
            "entity_ids": [entity["id"] for entity in matched_entities],
            "retrieval_policy": "recall_heavy_related_graph_context",
        }

    def _select_retrieval_method(self, entity_type: str) -> str:
        if entity_type == "Symptom":
            return "retrieve_by_symptom"
        if entity_type == "FailureMode":
            return "retrieve_by_failure"
        if entity_type in ("Cause", "Parameter", "Part", "Module",
                           "Mitigation", "OperatingFactor", "Method", "Engine"):
            return "retrieve_by_connected_entity"
        return "retrieve_by_query_plan"

    @staticmethod
    def _dedupe(items: List[str]) -> List[str]:
        seen = set()
        result = []
        for item in items:
            clean = item.strip().lower()
            if not clean or clean in seen:
                continue
            seen.add(clean)
            result.append(clean)
        return result
