{
  "metadata": {
    "name": "AeroOps Turbofan Maintenance GraphRAG dataset - cleaned visual import",
    "description": "Issue -> cause -> mitigation knowledge graph extracted from the AeroOPS_KnowledgeBASE turbofan corpus, with full claim-level provenance to source documents and passages.",
    "version": "1.1-cleaned",
    "generated": "2026-06-16",
    "target_database": "aeroops",
    "schema_version": "1.0",
    "embedding_note": "Chunk.embedding is null; populate during ingestion with your embedder (set vector index dimensions to match).",
    "counts": {
      "documents": 7,
      "chunks": 74,
      "nodes_total": 111,
      "nodes_by_label": {
        "Engine": 6,
        "Module": 7,
        "Part": 11,
        "Parameter": 10,
        "FailureMode": 21,
        "Symptom": 17,
        "Cause": 13,
        "Mitigation": 14,
        "OperatingFactor": 6,
        "Method": 6
      },
      "claims": 75,
      "reasoning_and_structural_relationships": 112,
      "mentioned_in_edges": 149
    },
    "cleaning_report": {
      "cleaned_generated": "2026-06-16",
      "nodes_removed_count": 37,
      "nodes_removed": [
        "C_contamination",
        "C_fatigue",
        "E_triple_spool",
        "E_twin_spool",
        "FM_engine_seizure",
        "FM_no_thrust_lever_response",
        "MC_dmc",
        "MC_llp",
        "MC_modular_design",
        "MC_on_condition",
        "MC_rul",
        "MC_shop_visit",
        "MC_svr",
        "MC_tbo",
        "MC_tow",
        "ME_cnn",
        "ME_extreme_random_forest",
        "ME_random_forest",
        "ME_rul_estimation",
        "ME_xgboost",
        "MI_airfoil_recontour",
        "MI_module_replacement",
        "MI_workscope_planning",
        "OF_derate",
        "OF_long_haul",
        "PA_n2",
        "PA_t48",
        "PA_t50",
        "PA_tip_clearance",
        "P_airfoil",
        "P_bearing",
        "P_disk",
        "P_seal",
        "P_shaft",
        "P_spool",
        "SY_chip_detector",
        "SY_smell_burnt"
      ],
      "node_renames": [
        {
          "from": "FM_high_oil_consumption",
          "to": "FM_oil_leak_or_oil_loss",
          "reason": "Original node represented oil leak/oil loss evidence more accurately than generic high oil consumption."
        }
      ],
      "duplicate_relationships_merged": [
        {
          "from": "C_particulate_ingestion",
          "to": "FM_airfoil_erosion",
          "type": "CAUSES",
          "claim_ids": [
            "CL007",
            "CL060"
          ],
          "source_chunk_ids": [
            "D1_c07",
            "D4_c06"
          ]
        }
      ],
      "import_scope": "visual knowledge graph: active knowledge nodes + main reasoning/structural relationships. Document chunks retained in JSON for provenance."
    }
  },
  "documents": [
    {
      "doc_id": "D1",
      "title": "Engine Maintenance Concepts for Financiers",
      "author": "Shannon Ackert",
      "year": 2011,
      "doc_type": "industry_paper",
      "publisher": "Aircraft Monitor",
      "file_id": "1fWN-VIWURIoBXAHZu3wglGNCEvF5gUfa",
      "view_url": "https://drive.google.com/file/d/1fWN-VIWURIoBXAHZu3wglGNCEvF5gUfa/view"
    },
    {
      "doc_id": "D2",
      "title": "Fault Prognosis of Turbofan Engines: Eventual Failure Prediction and RUL Estimation",
      "author": "Cohen, Huan, Ni",
      "year": 2022,
      "doc_type": "research_paper",
      "publisher": "PHM Society (open access, CC-BY)",
      "file_id": "1xEPKcPxd2SHRvoYCBMvj6WPXj7ZcQ0nK",
      "view_url": "https://drive.google.com/file/d/1xEPKcPxd2SHRvoYCBMvj6WPXj7ZcQ0nK/view"
    },
    {
      "doc_id": "D3",
      "title": "Airplane Turbofan Engine Operation and Malfunctions: Basic Familiarization for Flight Crews",
      "author": "FAA / Boeing",
      "year": 2010,
      "doc_type": "training_handbook",
      "publisher": "FAA",
      "file_id": "1ok4A2LyWIsRfDurEvfNHB3OG5ZZuQigP",
      "view_url": "https://drive.google.com/file/d/1ok4A2LyWIsRfDurEvfNHB3OG5ZZuQigP/view"
    },
    {
      "doc_id": "D4",
      "title": "Performance Deterioration of Commercial High-Bypass Ratio Turbofan Engines (NASA TM-81552)",
      "author": "Mehalic, Ziemianski",
      "year": 1980,
      "doc_type": "research_memorandum",
      "publisher": "NASA Lewis Research Center (public domain)",
      "file_id": "1wHWZxLghnbFmXXl7MwVxtxThc4GW1dk-",
      "view_url": "https://drive.google.com/file/d/1wHWZxLghnbFmXXl7MwVxtxThc4GW1dk-/view"
    },
    {
      "doc_id": "D5",
      "title": "Aircraft Turbine Engine Control Research at NASA Glenn Research Center (NASA TM-2013-217821)",
      "author": "Sanjay Garg",
      "year": 2013,
      "doc_type": "research_memorandum",
      "publisher": "NASA Glenn Research Center (public domain)",
      "file_id": "19oEvsgRnuSDZVsbzeA0tiBK-A5O0lV7H",
      "view_url": "https://drive.google.com/file/d/19oEvsgRnuSDZVsbzeA0tiBK-A5O0lV7H/view"
    },
    {
      "doc_id": "D6",
      "title": "Explainable Artificial Intelligence for Exhaust Gas Temperature of Turbofan Engines",
      "author": "Kefalas et al.",
      "year": 2021,
      "doc_type": "research_paper",
      "publisher": "Leiden University / KLM",
      "file_id": "10j8JCJDB3GP7n-RBuHd6kAxPeK_LGhHi",
      "view_url": "https://drive.google.com/file/d/10j8JCJDB3GP7n-RBuHd6kAxPeK_LGhHi/view"
    },
    {
      "doc_id": "D7",
      "title": "AMT Handbook - Powerplant, Ch.10 Engine Maintenance & Operation (FAA-H-8083-32B)",
      "author": "FAA",
      "year": 2018,
      "doc_type": "training_handbook",
      "publisher": "FAA (public domain)",
      "file_id": "1L4vsCNdJlCZ1bLjAm3LWRc0tI-uo9SJJ",
      "view_url": "https://drive.google.com/file/d/1L4vsCNdJlCZ1bLjAm3LWRc0tI-uo9SJJ/view"
    }
  ],
  "chunks": [
    {
      "chunk_id": "D1_c01",
      "doc_id": "D1",
      "section": "8.1 EGT Margin Deterioration",
      "page": 17,
      "text": "a major factor in deterioration of engine efficiency is the gradual increase in the clearance between the turbine blade tips and surrounding static seals or shrouds",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D1_c02",
      "doc_id": "D1",
      "section": "8.1 EGT Margin Deterioration",
      "page": 17,
      "text": "Such leakage reduces overall engine efficiency hence raising the total specific fuel consumption",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D1_c03",
      "doc_id": "D1",
      "section": "8.1 EGT Margin Deterioration",
      "page": 18,
      "text": "Rates of deterioration are highest in the initial 1,000 - 2,000 engine flight cycles of operation as the blade tips begin to wear",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D1_c04",
      "doc_id": "D1",
      "section": "10.1 Thrust Rating",
      "page": 21,
      "text": "Higher thrust generates higher core temperatures, which exposes constituent parts in the engine to greater thermal stress",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D1_c05",
      "doc_id": "D1",
      "section": "10.2 Operational Severity",
      "page": 22,
      "text": "A larger derate translates into lower take-off EGT and therefore enjoys a lower engine deterioration rate",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D1_c06",
      "doc_id": "D1",
      "section": "10.2 Operational Severity",
      "page": 23,
      "text": "Engines operated in dusty, sandy and erosive-corrosive environments are exposed to higher blade distress",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D1_c07",
      "doc_id": "D1",
      "section": "10.2 Operational Severity",
      "page": 23,
      "text": "Particulate material due to air pollution, such as dust, sand or industry emissions can erode HPC blades",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D1_c08",
      "doc_id": "D1",
      "section": "10.2 Operational Severity",
      "page": 23,
      "text": "and block HPT vane/blade cooling holes",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D1_c09",
      "doc_id": "D1",
      "section": "8.1 Water Washing",
      "page": 19,
      "text": "Engine wash provides increased EGT margin - thus longer on-wing life - and compressor efficiency resulting in reduced fuel burn",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D1_c10",
      "doc_id": "D1",
      "section": "8.1 Water Washing",
      "page": 19,
      "text": "this contamination leads to performance deterioration which can be restored by regular engine wash",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D1_c11",
      "doc_id": "D1",
      "section": "7.2 Shop Maintenance Elements",
      "page": 9,
      "text": "the core module is traditionally dismantled and airfoils (rotors & stators) are inspected, balanced, and repaired or replaced as necessary",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D1_c12",
      "doc_id": "D1",
      "section": "7.3 On-Condition Monitoring",
      "page": 10,
      "text": "used to inspect the internal parts of the engine for defects such as cracks, stress fractures and corrosion",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D1_c13",
      "doc_id": "D1",
      "section": "7.3 On-Condition Monitoring",
      "page": 10,
      "text": "regular detailed measurements are taken of the engine's operating speed, temperature, pressure, fuel flow and vibration levels",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D1_c14",
      "doc_id": "D1",
      "section": "8.3 Hardware Deterioration",
      "page": 19,
      "text": "blade distress (particularly on HPT blades), parts cracking and chipping, and in extreme situations, part failures",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D1_c15",
      "doc_id": "D1",
      "section": "8.4 Foreign Object Damage",
      "page": 20,
      "text": "FOD results from ingestion of foreign objects ... birds, ice, hail, ash, etc. as well as runway debris",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D1_c16",
      "doc_id": "D1",
      "section": "8.2 LLP Expiry",
      "page": 19,
      "text": "these engines are operating on short-to-medium haul networks and accumulate enough flight cycles to bump-up against a LLPs stub-life",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D1_c17",
      "doc_id": "D1",
      "section": "7.2 Shop Maintenance Elements",
      "page": 9,
      "text": "the parts must be replaced and not used again",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D1_c18",
      "doc_id": "D1",
      "section": "10.2 Operational Severity",
      "page": 21,
      "text": "the effect of shorter stage length operation is more rapid performance deterioration",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D1_c19",
      "doc_id": "D1",
      "section": "10.2 Operational Severity",
      "page": 22,
      "text": "an engine exposed to high ambient temperatures will experience lower available EGT margin and greater performance degradation",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D1_c20",
      "doc_id": "D1",
      "section": "10.3 Engine Age",
      "page": 24,
      "text": "As the engine ages a disproportionate amount of parts experience higher deterioration rates, higher scrap rates",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D1_c21",
      "doc_id": "D1",
      "section": "5.3 EGT",
      "page": 7,
      "text": "High EGT can be an indication of degraded engine performance",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D3_c01",
      "doc_id": "D3",
      "section": "Ch4 Compressor surge",
      "page": 18,
      "text": "The air flowing over the compressor airfoils can stall ... the compressor can no longer compress the incoming air",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D3_c02",
      "doc_id": "D3",
      "section": "Ch4 Compressor surge",
      "page": 18,
      "text": "Compressor surge may be caused by engine deterioration, it may be the result of ingestion of birds or ice",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D3_c03",
      "doc_id": "D3",
      "section": "Ch4 Compressor surge",
      "page": 18,
      "text": "the flight crew will hear a very loud bang, which will be accompanied by yaw and vibration",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D3_c04",
      "doc_id": "D3",
      "section": "Ch4 Compressor surge",
      "page": 18,
      "text": "Engine surge can be accompanied by visible flames forward out the inlet and rearward out the tailpipe",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D3_c05",
      "doc_id": "D3",
      "section": "Ch4 Compressor surge",
      "page": 18,
      "text": "Instruments may show high EGT and EPR or rotor speed changes",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D3_c06",
      "doc_id": "D3",
      "section": "Ch4 Surge recoverable after crew action",
      "page": 21,
      "text": "The desired pilot action is to retard the thrust lever until the engine recovers",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D3_c07",
      "doc_id": "D3",
      "section": "Ch4 Compressor surge",
      "page": 19,
      "text": "sustained surging will eventually over-heat the turbine ... Compressor blades may also be damaged and fail",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D3_c08",
      "doc_id": "D3",
      "section": "Ch4 Flameout",
      "page": 21,
      "text": "The flameout may result from the engine running out of fuel ... a control system malfunction, or unstable engine operation",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D3_c09",
      "doc_id": "D3",
      "section": "Ch4 Flameout",
      "page": 21,
      "text": "unstable engine operation (such as a compressor stall)",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D3_c10",
      "doc_id": "D3",
      "section": "Ch4 Flameout",
      "page": 21,
      "text": "A flameout will be accompanied by a drop in EGT, in engine core speed and in engine pressure ratio",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D3_c11",
      "doc_id": "D3",
      "section": "Ch4 Flameout",
      "page": 21,
      "text": "there may be other symptoms, such as low oil pressure warnings and electrical generators dropping off line",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D3_c12",
      "doc_id": "D3",
      "section": "Ch2 Ignition system",
      "page": 11,
      "text": "With continuous ignition, combustion will restart automatically, often without the pilot even noticing",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D3_c13",
      "doc_id": "D3",
      "section": "Ch3 EPR",
      "page": 14,
      "text": "A low EPR reading may be caused by engine rollback or flameout, or internal damage such as an LP turbine failure",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D3_c14",
      "doc_id": "D3",
      "section": "Ch3 EPR",
      "page": 14,
      "text": "Rapid EPR fluctuations may be caused by engine operational instability, such as surge",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D3_c15",
      "doc_id": "D3",
      "section": "Ch3 EGT",
      "page": 15,
      "text": "Excessive EGT is a key indicator of engine stall, of difficulty in engine starting, of a major bleed air leak",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D3_c16",
      "doc_id": "D3",
      "section": "Ch4 Vibration",
      "page": 28,
      "text": "Fan unbalance at assembly ... Bird ingestion/FOD ... Bearing failure ... Excessive fan rotor system tip clearances",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D3_c17",
      "doc_id": "D3",
      "section": "Ch4 Bearing failures",
      "page": 26,
      "text": "Bearing failures will be accompanied by an increase in oil temperature and indicated vibration",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D3_c18",
      "doc_id": "D3",
      "section": "Ch2 Lubrication system",
      "page": 10,
      "text": "Chip detectors ... to collect bearing compartment particles as an indication of bearing compartment distress",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D3_c19",
      "doc_id": "D3",
      "section": "Ch4 Oil leaks",
      "page": 26,
      "text": "Leaks will produce a sustained reduction in oil quantity, down to zero",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D3_c20",
      "doc_id": "D3",
      "section": "Ch3 Oil Filter Bypass",
      "page": 16,
      "text": "If the oil filter becomes clogged with debris (either from contamination ... or debris from a bearing failure)",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D3_c21",
      "doc_id": "D3",
      "section": "Ch4 Tailpipe Fires",
      "page": 23,
      "text": "Fuel may puddle in the turbine casings and exhaust during start-up or shutdown, and then ignite",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D3_c22",
      "doc_id": "D3",
      "section": "Ch4 Tailpipe Fires",
      "page": 23,
      "text": "dry motor the engine, which is the quickest way of extinguishing most tailpipe fires",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D3_c23",
      "doc_id": "D3",
      "section": "Ch4 Fire",
      "page": 22,
      "text": "A fire in the vicinity of the engine should be annunciated to the flight crew by a fire warning in the flight deck",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D3_c24",
      "doc_id": "D3",
      "section": "Ch4 Fire",
      "page": 22,
      "text": "engine shutdown should be immediately accomplished by shutting off fuel to the engine",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D3_c25",
      "doc_id": "D3",
      "section": "Ch4 Hot starts",
      "page": 23,
      "text": "Normal engine cooling flows will not be effective during sub-idle operation, and turbine temperatures may appear relatively high",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D3_c26",
      "doc_id": "D3",
      "section": "Ch4 Vibration",
      "page": 28,
      "text": "fan blade material loss due to ingested material, or fan blade distortion due to foreign object damage",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D3_c27",
      "doc_id": "D3",
      "section": "Ch4 Bird ingestion/FOD",
      "page": 24,
      "text": "Bird ingestion can result in the fracture of one or more fan blades, in which case, the engine will likely surge once and not recover",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D3_c28",
      "doc_id": "D3",
      "section": "Ch4 Bird ingestion/FOD",
      "page": 24,
      "text": "The photo on the next page shows fan blades bent due to the ingestion of a bird",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D3_c29",
      "doc_id": "D3",
      "section": "Ch4 Fuel filter Clogging",
      "page": 26,
      "text": "Fuel filter clogging can result from the failure of one of the fuel tank boost pumps",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D3_c30",
      "doc_id": "D3",
      "section": "Ch4 Fuel filter Clogging",
      "page": 26,
      "text": "There is potential for multiple-engine flameout",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D3_c31",
      "doc_id": "D3",
      "section": "Ch4 Severe engine damage",
      "page": 24,
      "text": "severe engine damage may be accompanied by symptoms such as fire warning ... or engine surge",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D1_c22",
      "doc_id": "D1",
      "section": "10.2 Operational Severity",
      "page": 23,
      "text": "Other environmental distress symptoms consist of hardware corrosion and oxidation",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D4_c01",
      "doc_id": "D4",
      "section": "Results and Discussion",
      "page": 4,
      "text": "Clearance increases resulting in efficiency losses occur ... as a result of blades rubbing their outer shrouds",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D4_c02",
      "doc_id": "D4",
      "section": "Testing for Specific Effects",
      "page": 9,
      "text": "a primary cause of engine performance deterioration was increased blade tip clearances throughout the engine",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D4_c03",
      "doc_id": "D4",
      "section": "Historical Data",
      "page": 4,
      "text": "The performance deterioration mechanisms - such as clearance increases ... affect the cruise specific fuel consumption (SFC)",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D4_c04",
      "doc_id": "D4",
      "section": "Historical Data",
      "page": 5,
      "text": "deflections produced by aircraft induced flight loads that occur during take off rotation, flight maneuvers, landing, and thrust reversal",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D4_c05",
      "doc_id": "D4",
      "section": "Historical Data",
      "page": 5,
      "text": "hot rotor reburst ... can result in high pressure turbine blade rubs due to different thermal growth rates between rotating and stationary structures",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D4_c06",
      "doc_id": "D4",
      "section": "Historical Data",
      "page": 4,
      "text": "airfoil Quality (foreign object damage (FOD), erosion, and surface roughness) is significant",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D4_c07",
      "doc_id": "D4",
      "section": "Historical Data",
      "page": 4,
      "text": "thermal distortion is one of the predominant deterioration mechanisms causing ... warpage or distortion of vanes",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D4_c08",
      "doc_id": "D4",
      "section": "Historical Data",
      "page": 6,
      "text": "High and low pressure turbine thermal distortion is also a contributing source to the long-term performance deterioration",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D4_c09",
      "doc_id": "D4",
      "section": "Historical Data",
      "page": 5,
      "text": "high pressure turbine clearance increases contribute over 90 percent of the total short-term performance deterioration",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D4_c10",
      "doc_id": "D4",
      "section": "Concluding Remarks",
      "page": 13,
      "text": "Long-term performance deterioration ... is about 2.5 to 3.0 percent cruise SFC",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D4_c11",
      "doc_id": "D4",
      "section": "Results and Discussion",
      "page": 6,
      "text": "not all performance deterioration is restored, there being a residual of approximately 0.2 percent cruise SFC",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D3_c32",
      "doc_id": "D3",
      "section": "Ch2 Cooling/clearance control bleeds",
      "page": 12,
      "text": "air extracted from the compressor is ducted and directed onto the engine cases to control the clearance between the rotor blade tips and the case wall",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D2_c01",
      "doc_id": "D2",
      "section": "1 Introduction",
      "page": 1,
      "text": "the goal of intelligent prognostic approaches is to predict the progression of degradation in advance ... before catastrophic failure",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D2_c02",
      "doc_id": "D2",
      "section": "Abstract",
      "page": 1,
      "text": "predict the current health state, the eventual failing component(s), and the remaining useful life",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D2_c03",
      "doc_id": "D2",
      "section": "3 Results",
      "page": 7,
      "text": "the PCA orthogonalization pre-processing step has a profound impact on classification performance",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D2_c04",
      "doc_id": "D2",
      "section": "1 Introduction",
      "page": 2,
      "text": "reduce reactive maintenance costs, which may account for up to 40% of the overall budget",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D2_c05",
      "doc_id": "D2",
      "section": "1 Introduction",
      "page": 1,
      "text": "7 possible failure modes that involve efficiency and/or flow failures of 5 rotating subcomponents",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D6_c01",
      "doc_id": "D6",
      "section": "Abstract",
      "page": 1,
      "text": "uncover meaningful algebraic relationships between the EGT and other measurable engine parameters",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D5_c01",
      "doc_id": "D5",
      "section": "Abstract",
      "page": 1,
      "text": "develop advanced propulsion controls and diagnostics technologies",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D7_c01",
      "doc_id": "D7",
      "section": "Ch10 General Overhaul Procedures",
      "page": 1,
      "text": "The major purpose of overhaul is to inspect, repair, and replace worn engine parts",
      "embedding": null,
      "char_start": null,
      "char_end": null
    },
    {
      "chunk_id": "D7_c02",
      "doc_id": "D7",
      "section": "Ch10 Overhaul Process",
      "page": 1,
      "text": "non-destructive testing (NDT) inspection",
      "embedding": null,
      "char_start": null,
      "char_end": null
    }
  ],
  "nodes": {
    "Engine": [
      {
        "id": "E_turbofan",
        "name": "Turbofan engine",
        "architecture": "axial-flow"
      },
      {
        "id": "E_high_bypass",
        "name": "High-bypass ratio turbofan",
        "architecture": "high-bypass"
      },
      {
        "id": "E_CFM56",
        "name": "CFM56",
        "oem": "CFM International"
      },
      {
        "id": "E_V2500",
        "name": "V2500",
        "oem": "International Aero Engines"
      },
      {
        "id": "E_JT9D",
        "name": "Pratt & Whitney JT9D",
        "oem": "Pratt & Whitney"
      },
      {
        "id": "E_CF6",
        "name": "General Electric CF6",
        "oem": "General Electric"
      }
    ],
    "Module": [
      {
        "id": "M_fan_lpc",
        "name": "Fan / Low-Pressure Compressor (LPC)",
        "section": "cold"
      },
      {
        "id": "M_hpc",
        "name": "High-Pressure Compressor (HPC)",
        "section": "core"
      },
      {
        "id": "M_combustor",
        "name": "Combustor",
        "section": "core"
      },
      {
        "id": "M_hpt",
        "name": "High-Pressure Turbine (HPT)",
        "section": "hot"
      },
      {
        "id": "M_lpt",
        "name": "Low-Pressure Turbine (LPT)",
        "section": "hot"
      },
      {
        "id": "M_accessory_drive",
        "name": "Accessory drive gearbox",
        "section": "cold"
      },
      {
        "id": "M_core",
        "name": "Core / hot section (HPC + combustor + HPT)",
        "section": "hot"
      }
    ],
    "Part": [
      {
        "id": "P_fan_blade",
        "name": "Fan blade",
        "is_llp": false,
        "material": "titanium/composite"
      },
      {
        "id": "P_fan_disk",
        "name": "Fan disk",
        "is_llp": true
      },
      {
        "id": "P_compressor_blade",
        "name": "Compressor rotor blade",
        "is_llp": false
      },
      {
        "id": "P_compressor_vane",
        "name": "Compressor stator vane",
        "is_llp": false
      },
      {
        "id": "P_hpt_blade",
        "name": "HPT blade",
        "is_llp": false
      },
      {
        "id": "P_lpt_blade",
        "name": "LPT blade",
        "is_llp": false
      },
      {
        "id": "P_nozzle_guide_vane",
        "name": "Nozzle guide vane",
        "is_llp": false
      },
      {
        "id": "P_shroud",
        "name": "Shroud / rub strip",
        "is_llp": false
      },
      {
        "id": "P_blade_tip",
        "name": "Blade tip",
        "is_llp": false
      },
      {
        "id": "P_fuel_nozzle",
        "name": "Fuel nozzle",
        "is_llp": false
      },
      {
        "id": "P_cooling_hole",
        "name": "HPT vane/blade cooling hole",
        "is_llp": false
      }
    ],
    "Parameter": [
      {
        "id": "PA_egt",
        "name": "Exhaust Gas Temperature (EGT)",
        "symbol": "EGT",
        "unit": "degC",
        "role": "health"
      },
      {
        "id": "PA_egt_margin",
        "name": "EGT margin",
        "unit": "degC",
        "role": "health"
      },
      {
        "id": "PA_n1",
        "name": "N1 fan speed",
        "symbol": "N1",
        "unit": "%RPM",
        "role": "thrust"
      },
      {
        "id": "PA_epr",
        "name": "Engine Pressure Ratio (EPR)",
        "symbol": "EPR",
        "unit": "ratio",
        "role": "thrust"
      },
      {
        "id": "PA_fuel_flow",
        "name": "Fuel flow",
        "unit": "pph",
        "role": "condition"
      },
      {
        "id": "PA_vibration",
        "name": "Vibration",
        "unit": "non-dimensional",
        "role": "condition"
      },
      {
        "id": "PA_oil_pressure",
        "name": "Oil pressure",
        "role": "condition"
      },
      {
        "id": "PA_oil_temp",
        "name": "Oil temperature",
        "role": "condition"
      },
      {
        "id": "PA_oil_quantity",
        "name": "Oil quantity",
        "role": "condition"
      },
      {
        "id": "PA_sfc",
        "name": "Specific Fuel Consumption (SFC)",
        "role": "performance"
      }
    ],
    "FailureMode": [
      {
        "id": "FM_egt_margin_deterioration",
        "name": "EGT margin deterioration",
        "category": "performance",
        "severity": "moderate"
      },
      {
        "id": "FM_tip_clearance_increase",
        "name": "Blade-tip clearance increase",
        "category": "mechanical",
        "severity": "moderate"
      },
      {
        "id": "FM_blade_tip_rub",
        "name": "Blade tip rub",
        "category": "mechanical",
        "severity": "moderate"
      },
      {
        "id": "FM_airfoil_erosion",
        "name": "Airfoil erosion / surface roughness",
        "category": "mechanical",
        "severity": "moderate"
      },
      {
        "id": "FM_thermal_distortion",
        "name": "Thermal distortion / vane warpage",
        "category": "thermal",
        "severity": "moderate"
      },
      {
        "id": "FM_hardware_deterioration",
        "name": "Hardware deterioration / blade distress",
        "category": "mechanical",
        "severity": "high"
      },
      {
        "id": "FM_fod",
        "name": "Foreign Object Damage (FOD)",
        "category": "mechanical",
        "severity": "high"
      },
      {
        "id": "FM_llp_expiry",
        "name": "Life-Limited Part (LLP) expiry",
        "category": "lifecycle",
        "severity": "scheduled"
      },
      {
        "id": "FM_compressor_surge",
        "name": "Compressor surge / stall",
        "category": "operational_instability",
        "severity": "high"
      },
      {
        "id": "FM_flameout",
        "name": "Flameout",
        "category": "operational",
        "severity": "high"
      },
      {
        "id": "FM_oil_leak_or_oil_loss",
        "name": "Oil leak / oil loss",
        "category": "lubrication",
        "severity": "moderate",
        "aliases": [
          "High oil consumption"
        ],
        "previous_id": "FM_high_oil_consumption"
      },
      {
        "id": "FM_bearing_failure",
        "name": "Bearing failure",
        "category": "mechanical",
        "severity": "high"
      },
      {
        "id": "FM_engine_fire",
        "name": "Engine (nacelle) fire",
        "category": "safety",
        "severity": "critical"
      },
      {
        "id": "FM_tailpipe_fire",
        "name": "Tailpipe fire",
        "category": "safety",
        "severity": "moderate"
      },
      {
        "id": "FM_hot_start",
        "name": "Hot start",
        "category": "operational",
        "severity": "moderate"
      },
      {
        "id": "FM_severe_engine_damage",
        "name": "Severe engine damage",
        "category": "mechanical",
        "severity": "critical"
      },
      {
        "id": "FM_blade_cracking",
        "name": "Blade cracking / chipping",
        "category": "mechanical",
        "severity": "high"
      },
      {
        "id": "FM_corrosion",
        "name": "Corrosion / oxidation",
        "category": "environmental",
        "severity": "moderate"
      },
      {
        "id": "FM_blocked_cooling_holes",
        "name": "Blocked HPT cooling holes",
        "category": "thermal",
        "severity": "high"
      },
      {
        "id": "FM_fuel_filter_clogging",
        "name": "Fuel filter clogging",
        "category": "fuel_system",
        "severity": "moderate"
      },
      {
        "id": "FM_fan_unbalance",
        "name": "Fan unbalance",
        "category": "mechanical",
        "severity": "moderate"
      }
    ],
    "Symptom": [
      {
        "id": "SY_high_egt",
        "name": "High / rising EGT"
      },
      {
        "id": "SY_egt_exceedance",
        "name": "EGT redline exceedance"
      },
      {
        "id": "SY_low_epr",
        "name": "Low EPR"
      },
      {
        "id": "SY_epr_fluctuation",
        "name": "Rapid EPR fluctuation"
      },
      {
        "id": "SY_low_n1",
        "name": "Low N1"
      },
      {
        "id": "SY_n1_fluctuation",
        "name": "Fluctuating N1"
      },
      {
        "id": "SY_loud_bang",
        "name": "Loud bang and yaw"
      },
      {
        "id": "SY_high_vibration",
        "name": "High vibration"
      },
      {
        "id": "SY_visible_flame",
        "name": "Visible flame from inlet / tailpipe"
      },
      {
        "id": "SY_rising_fuel_flow",
        "name": "Rising fuel flow"
      },
      {
        "id": "SY_high_fuel_flow",
        "name": "Abnormally high fuel flow"
      },
      {
        "id": "SY_low_oil_pressure",
        "name": "Low oil pressure"
      },
      {
        "id": "SY_high_oil_temp",
        "name": "High oil temperature"
      },
      {
        "id": "SY_decreasing_oil_quantity",
        "name": "Steady decrease in oil quantity"
      },
      {
        "id": "SY_oil_filter_bypass",
        "name": "Oil filter bypass indication"
      },
      {
        "id": "SY_fire_warning",
        "name": "Fire warning"
      },
      {
        "id": "SY_sfc_increase",
        "name": "Cruise SFC increase / higher fuel burn"
      }
    ],
    "Cause": [
      {
        "id": "C_particulate_ingestion",
        "name": "Particulate / dust / sand ingestion",
        "type": "environmental"
      },
      {
        "id": "C_fod_ingestion",
        "name": "Foreign object / bird ingestion",
        "type": "environmental"
      },
      {
        "id": "C_thermal_stress",
        "name": "Thermal stress / high core temperature",
        "type": "thermal"
      },
      {
        "id": "C_blade_tip_wear",
        "name": "Blade tip wear",
        "type": "mechanical"
      },
      {
        "id": "C_flight_loads",
        "name": "Flight loads (aerodynamic + inertial)",
        "type": "operational"
      },
      {
        "id": "C_hot_rotor_reburst",
        "name": "Hot rotor reburst (thermal transient)",
        "type": "thermal"
      },
      {
        "id": "C_rotor_case_interference",
        "name": "Rotor / case interference",
        "type": "mechanical"
      },
      {
        "id": "C_compressor_airfoil_stall",
        "name": "Compressor airfoil aerodynamic stall",
        "type": "aerodynamic"
      },
      {
        "id": "C_fuel_starvation",
        "name": "Fuel starvation / interruption",
        "type": "operational"
      },
      {
        "id": "C_bearing_distress",
        "name": "Bearing distress",
        "type": "mechanical"
      },
      {
        "id": "C_combustion_heat",
        "name": "Combustion heat / oxidation",
        "type": "thermal"
      },
      {
        "id": "C_fuel_puddling",
        "name": "Fuel puddling in tailpipe",
        "type": "operational"
      },
      {
        "id": "C_boost_pump_failure",
        "name": "Fuel boost-pump debris",
        "type": "mechanical"
      }
    ],
    "Mitigation": [
      {
        "id": "MI_water_wash",
        "name": "Engine water washing",
        "type": "preventive"
      },
      {
        "id": "MI_takeoff_derate",
        "name": "Take-off derate",
        "type": "operational"
      },
      {
        "id": "MI_performance_restoration",
        "name": "Performance restoration shop visit",
        "type": "corrective"
      },
      {
        "id": "MI_llp_replacement",
        "name": "LLP replacement",
        "type": "corrective"
      },
      {
        "id": "MI_borescope_inspection",
        "name": "Borescope inspection",
        "type": "inspection"
      },
      {
        "id": "MI_on_condition_monitoring",
        "name": "On-condition / trend monitoring",
        "type": "preventive"
      },
      {
        "id": "MI_overhaul",
        "name": "Engine overhaul / full teardown",
        "type": "corrective"
      },
      {
        "id": "MI_ndt",
        "name": "Non-destructive testing (NDT) inspection",
        "type": "inspection"
      },
      {
        "id": "MI_thrust_reduction",
        "name": "Thrust reduction (retard thrust lever)",
        "type": "operational"
      },
      {
        "id": "MI_engine_shutdown",
        "name": "Engine shutdown",
        "type": "operational"
      },
      {
        "id": "MI_continuous_ignition",
        "name": "Continuous ignition",
        "type": "operational"
      },
      {
        "id": "MI_clearance_control_bleed",
        "name": "Active clearance control (case cooling bleed)",
        "type": "design"
      },
      {
        "id": "MI_predictive_maintenance",
        "name": "Predictive maintenance (RUL / PHM)",
        "type": "preventive"
      },
      {
        "id": "MI_dry_motoring",
        "name": "Dry motoring the engine",
        "type": "operational"
      }
    ],
    "OperatingFactor": [
      {
        "id": "OF_flight_length",
        "name": "Flight length / sector length"
      },
      {
        "id": "OF_oat",
        "name": "Outside air temperature (OAT)"
      },
      {
        "id": "OF_environment",
        "name": "Operating environment (dusty / erosive / temperate)"
      },
      {
        "id": "OF_thrust_rating",
        "name": "Thrust rating"
      },
      {
        "id": "OF_engine_age",
        "name": "Engine age / phase (first-run vs mature)"
      },
      {
        "id": "OF_short_haul",
        "name": "Short-haul / high-cycle operation"
      }
    ],
    "Method": [
      {
        "id": "ME_ann_flux",
        "name": "ANN-Flux (custom-loss neural network)",
        "family": "deep_learning"
      },
      {
        "id": "ME_pca",
        "name": "PCA orthogonalization",
        "family": "preprocessing"
      },
      {
        "id": "ME_phm",
        "name": "Prognostics & Health Management (PHM)",
        "family": "framework"
      },
      {
        "id": "ME_symbolic_regression",
        "name": "Symbolic regression (EGT modeling)",
        "family": "interpretable_ml"
      },
      {
        "id": "ME_fadec",
        "name": "FADEC / EEC engine control",
        "family": "control"
      },
      {
        "id": "ME_ncmapss",
        "name": "N-CMAPSS run-to-failure dataset",
        "family": "benchmark"
      }
    ]
  },
  "claims": [
    {
      "claim_id": "CL001",
      "predicate": "DEGRADES",
      "statement": "Growth of clearance between turbine blade tips and static seals/shrouds raises flow losses and erodes EGT margin.",
      "subject": "FM_tip_clearance_increase",
      "object": "PA_egt_margin",
      "confidence": 0.95,
      "source_chunk_ids": [
        "D1_c01"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL002",
      "predicate": "CAUSES",
      "statement": "Tip-clearance growth reduces engine efficiency and is the primary driver of EGT margin deterioration.",
      "subject": "FM_tip_clearance_increase",
      "object": "FM_egt_margin_deterioration",
      "confidence": 0.9,
      "source_chunk_ids": [
        "D1_c02"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL003",
      "predicate": "CAUSES",
      "statement": "Blade tips wearing during the initial flight cycles open up running clearances.",
      "subject": "C_blade_tip_wear",
      "object": "FM_tip_clearance_increase",
      "confidence": 0.85,
      "source_chunk_ids": [
        "D1_c03"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL004",
      "predicate": "INFLUENCES",
      "statement": "Higher thrust raises core temperatures and thermal stress, accelerating EGT margin deterioration.",
      "subject": "OF_thrust_rating",
      "object": "FM_egt_margin_deterioration",
      "confidence": 0.9,
      "source_chunk_ids": [
        "D1_c04"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL005",
      "predicate": "MITIGATES",
      "statement": "Take-off derate lowers take-off EGT, slowing the deterioration rate and extending time on-wing.",
      "subject": "MI_takeoff_derate",
      "object": "FM_egt_margin_deterioration",
      "confidence": 0.9,
      "source_chunk_ids": [
        "D1_c05"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL006",
      "predicate": "INFLUENCES",
      "statement": "Dusty, sandy and erosive-corrosive environments raise blade distress and performance deterioration.",
      "subject": "OF_environment",
      "object": "FM_airfoil_erosion",
      "confidence": 0.9,
      "source_chunk_ids": [
        "D1_c06"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL007",
      "predicate": "CAUSES",
      "statement": "Airborne particulates (dust, sand, industrial emissions) erode HPC blades.",
      "subject": "C_particulate_ingestion",
      "object": "FM_airfoil_erosion",
      "confidence": 0.9,
      "source_chunk_ids": [
        "D1_c07"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL008",
      "predicate": "CAUSES",
      "statement": "Ingested particulates block HPT vane and blade cooling holes.",
      "subject": "C_particulate_ingestion",
      "object": "FM_blocked_cooling_holes",
      "confidence": 0.9,
      "source_chunk_ids": [
        "D1_c08"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL009",
      "predicate": "RESTORES",
      "statement": "On-wing water washing cleans the gas path, recovering EGT margin and compressor efficiency.",
      "subject": "MI_water_wash",
      "object": "PA_egt_margin",
      "confidence": 0.9,
      "source_chunk_ids": [
        "D1_c09"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL010",
      "predicate": "MITIGATES",
      "statement": "Regular water washing offsets contamination-driven EGT margin erosion.",
      "subject": "MI_water_wash",
      "object": "FM_egt_margin_deterioration",
      "confidence": 0.85,
      "source_chunk_ids": [
        "D1_c10"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL011",
      "predicate": "MITIGATES",
      "statement": "Core teardown inspects and repairs/replaces airfoils to restore lost performance.",
      "subject": "MI_performance_restoration",
      "object": "FM_hardware_deterioration",
      "confidence": 0.9,
      "source_chunk_ids": [
        "D1_c11"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL012",
      "predicate": "DETECTS",
      "statement": "Borescopes inspect internal parts for cracks, stress fractures and corrosion.",
      "subject": "MI_borescope_inspection",
      "object": "FM_blade_cracking",
      "confidence": 0.9,
      "source_chunk_ids": [
        "D1_c12"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL013",
      "predicate": "DETECTS",
      "statement": "Trend monitoring of EGT, fuel flow, vibration and oil consumption identifies deteriorating engines early.",
      "subject": "MI_on_condition_monitoring",
      "object": "FM_egt_margin_deterioration",
      "confidence": 0.85,
      "source_chunk_ids": [
        "D1_c13"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL014",
      "predicate": "AFFECTS",
      "statement": "Hardware deterioration shows up as blade distress, especially on HPT blades, plus cracking and chipping.",
      "subject": "FM_hardware_deterioration",
      "object": "P_hpt_blade",
      "confidence": 0.85,
      "source_chunk_ids": [
        "D1_c14"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL015",
      "predicate": "CAUSES",
      "statement": "Ingestion of birds, ice, hail, ash and runway debris produces foreign object damage.",
      "subject": "C_fod_ingestion",
      "object": "FM_fod",
      "confidence": 0.95,
      "source_chunk_ids": [
        "D1_c15"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL016",
      "predicate": "INFLUENCES",
      "statement": "Short-haul, high-cycle operation accumulates flight cycles fast, driving engines into LLP stub-life limits.",
      "subject": "OF_short_haul",
      "object": "FM_llp_expiry",
      "confidence": 0.85,
      "source_chunk_ids": [
        "D1_c16"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL017",
      "predicate": "MITIGATES",
      "statement": "Replacing life-limited parts at their cyclic limit resolves LLP expiry removals.",
      "subject": "MI_llp_replacement",
      "object": "FM_llp_expiry",
      "confidence": 0.9,
      "source_chunk_ids": [
        "D1_c17"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL018",
      "predicate": "INFLUENCES",
      "statement": "Shorter sector lengths spend more time at take-off/climb power, accelerating performance deterioration.",
      "subject": "OF_flight_length",
      "object": "FM_egt_margin_deterioration",
      "confidence": 0.9,
      "source_chunk_ids": [
        "D1_c18"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL019",
      "predicate": "INFLUENCES",
      "statement": "High ambient temperatures lower available EGT margin and increase performance degradation.",
      "subject": "OF_oat",
      "object": "FM_egt_margin_deterioration",
      "confidence": 0.9,
      "source_chunk_ids": [
        "D1_c19"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL020",
      "predicate": "INFLUENCES",
      "statement": "As engines age, hardware deterioration and scrap rates rise.",
      "subject": "OF_engine_age",
      "object": "FM_hardware_deterioration",
      "confidence": 0.85,
      "source_chunk_ids": [
        "D1_c20"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL021",
      "predicate": "MANIFESTS_AS",
      "statement": "As margin erodes, EGT rises toward redline at constant thrust.",
      "subject": "FM_egt_margin_deterioration",
      "object": "SY_high_egt",
      "confidence": 0.85,
      "source_chunk_ids": [
        "D1_c21"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL022",
      "predicate": "CAUSES",
      "statement": "Aerodynamic stall of compressor airfoils makes airflow unstable so high-pressure air bursts forward out the inlet.",
      "subject": "C_compressor_airfoil_stall",
      "object": "FM_compressor_surge",
      "confidence": 0.9,
      "source_chunk_ids": [
        "D3_c01"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL023",
      "predicate": "CAUSES",
      "statement": "Bird or ice ingestion can trigger a compressor surge.",
      "subject": "C_fod_ingestion",
      "object": "FM_compressor_surge",
      "confidence": 0.85,
      "source_chunk_ids": [
        "D3_c02"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL024",
      "predicate": "MANIFESTS_AS",
      "statement": "A high-power surge produces a very loud bang accompanied by yaw and vibration.",
      "subject": "FM_compressor_surge",
      "object": "SY_loud_bang",
      "confidence": 0.95,
      "source_chunk_ids": [
        "D3_c03"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL025",
      "predicate": "MANIFESTS_AS",
      "statement": "Surge can show visible flames forward out the inlet and rearward out the tailpipe.",
      "subject": "FM_compressor_surge",
      "object": "SY_visible_flame",
      "confidence": 0.85,
      "source_chunk_ids": [
        "D3_c04"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL026",
      "predicate": "MANIFESTS_AS",
      "statement": "Surge instruments may show high EGT and EPR or rotor-speed changes.",
      "subject": "FM_compressor_surge",
      "object": "SY_high_egt",
      "confidence": 0.8,
      "source_chunk_ids": [
        "D3_c05"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL027",
      "predicate": "MITIGATES",
      "statement": "Retarding the thrust lever lets a surging engine recover.",
      "subject": "MI_thrust_reduction",
      "object": "FM_compressor_surge",
      "confidence": 0.9,
      "source_chunk_ids": [
        "D3_c06"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL028",
      "predicate": "LEADS_TO",
      "statement": "Sustained surging overheats the turbine and can damage compressor blades, progressing to severe damage.",
      "subject": "FM_compressor_surge",
      "object": "FM_severe_engine_damage",
      "confidence": 0.85,
      "source_chunk_ids": [
        "D3_c07"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL029",
      "predicate": "CAUSES",
      "statement": "Loss or interruption of fuel stops combustion and causes a flameout.",
      "subject": "C_fuel_starvation",
      "object": "FM_flameout",
      "confidence": 0.9,
      "source_chunk_ids": [
        "D3_c08"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL030",
      "predicate": "LEADS_TO",
      "statement": "Unstable engine operation such as a compressor stall can lead to flameout.",
      "subject": "FM_compressor_surge",
      "object": "FM_flameout",
      "confidence": 0.8,
      "source_chunk_ids": [
        "D3_c09"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL031",
      "predicate": "MANIFESTS_AS",
      "statement": "Flameout brings a drop in EGT, core speed and engine pressure ratio.",
      "subject": "FM_flameout",
      "object": "SY_low_epr",
      "confidence": 0.9,
      "source_chunk_ids": [
        "D3_c10"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL032",
      "predicate": "MANIFESTS_AS",
      "statement": "Once speed drops below idle, low oil pressure warnings and generators dropping off-line appear.",
      "subject": "FM_flameout",
      "object": "SY_low_oil_pressure",
      "confidence": 0.8,
      "source_chunk_ids": [
        "D3_c11"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL033",
      "predicate": "MITIGATES",
      "statement": "Continuous ignition automatically restarts combustion if it is interrupted.",
      "subject": "MI_continuous_ignition",
      "object": "FM_flameout",
      "confidence": 0.85,
      "source_chunk_ids": [
        "D3_c12"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL034",
      "predicate": "INDICATES",
      "statement": "A low EPR reading can indicate engine rollback, flameout or LP turbine failure.",
      "subject": "SY_low_epr",
      "object": "FM_flameout",
      "confidence": 0.85,
      "source_chunk_ids": [
        "D3_c13"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL035",
      "predicate": "INDICATES",
      "statement": "Rapid EPR fluctuations can indicate operational instability such as surge.",
      "subject": "SY_epr_fluctuation",
      "object": "FM_compressor_surge",
      "confidence": 0.85,
      "source_chunk_ids": [
        "D3_c14"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL036",
      "predicate": "INDICATES",
      "statement": "Excessive EGT is a key indicator of stall, start difficulty, bleed leak or severe damage.",
      "subject": "SY_egt_exceedance",
      "object": "FM_severe_engine_damage",
      "confidence": 0.8,
      "source_chunk_ids": [
        "D3_c15"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL037",
      "predicate": "INDICATES",
      "statement": "Vibration can stem from fan unbalance, blade icing, FOD, bearing failure, blade distortion or excessive tip clearance.",
      "subject": "SY_high_vibration",
      "object": "FM_fan_unbalance",
      "confidence": 0.8,
      "source_chunk_ids": [
        "D3_c16"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL038",
      "predicate": "INDICATES",
      "statement": "Indicated vibration accompanies bearing failure.",
      "subject": "SY_high_vibration",
      "object": "FM_bearing_failure",
      "confidence": 0.8,
      "source_chunk_ids": [
        "D3_c17"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL039",
      "predicate": "MANIFESTS_AS",
      "statement": "Bearing failure raises oil temperature.",
      "subject": "FM_bearing_failure",
      "object": "SY_high_oil_temp",
      "confidence": 0.85,
      "source_chunk_ids": [
        "D3_c17"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL040",
      "predicate": "CAUSES",
      "statement": "Bearing-compartment distress, signalled by chip detectors, precedes bearing failure.",
      "subject": "C_bearing_distress",
      "object": "FM_bearing_failure",
      "confidence": 0.75,
      "source_chunk_ids": [
        "D3_c18"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL041",
      "predicate": "MANIFESTS_AS",
      "statement": "An oil leak produces a sustained decrease in oil quantity.",
      "subject": "FM_oil_leak_or_oil_loss",
      "object": "SY_decreasing_oil_quantity",
      "confidence": 0.85,
      "source_chunk_ids": [
        "D3_c19"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL042",
      "predicate": "INDICATES",
      "statement": "Oil filter clogging/bypass can come from bearing-failure debris or contamination.",
      "subject": "SY_oil_filter_bypass",
      "object": "FM_bearing_failure",
      "confidence": 0.75,
      "source_chunk_ids": [
        "D3_c20"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL043",
      "predicate": "CAUSES",
      "statement": "Fuel puddling in the turbine casing/exhaust during start or shutdown ignites as a tailpipe fire.",
      "subject": "C_fuel_puddling",
      "object": "FM_tailpipe_fire",
      "confidence": 0.9,
      "source_chunk_ids": [
        "D3_c21"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL044",
      "predicate": "MITIGATES",
      "statement": "Dry motoring the engine is the quickest way to extinguish most tailpipe fires.",
      "subject": "MI_dry_motoring",
      "object": "FM_tailpipe_fire",
      "confidence": 0.85,
      "source_chunk_ids": [
        "D3_c22"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL045",
      "predicate": "MANIFESTS_AS",
      "statement": "A nacelle fire is annunciated by a flight-deck fire warning.",
      "subject": "FM_engine_fire",
      "object": "SY_fire_warning",
      "confidence": 0.85,
      "source_chunk_ids": [
        "D3_c23"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL046",
      "predicate": "MITIGATES",
      "statement": "Once a fire is confirmed, shutting off fuel and discharging extinguishant controls it.",
      "subject": "MI_engine_shutdown",
      "object": "FM_engine_fire",
      "confidence": 0.85,
      "source_chunk_ids": [
        "D3_c24"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL047",
      "predicate": "MANIFESTS_AS",
      "statement": "Prolonged sub-idle operation during start gives poor cooling and high turbine temperatures (hot start).",
      "subject": "FM_hot_start",
      "object": "SY_high_egt",
      "confidence": 0.85,
      "source_chunk_ids": [
        "D3_c25"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL048",
      "predicate": "CAUSES",
      "statement": "FOD can cause fan-blade material loss or distortion, unbalancing the fan.",
      "subject": "C_fod_ingestion",
      "object": "FM_fan_unbalance",
      "confidence": 0.8,
      "source_chunk_ids": [
        "D3_c26"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL049",
      "predicate": "LEADS_TO",
      "statement": "FOD / bird ingestion can fracture fan blades and trigger an unrecoverable surge.",
      "subject": "FM_fod",
      "object": "FM_compressor_surge",
      "confidence": 0.8,
      "source_chunk_ids": [
        "D3_c27"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL050",
      "predicate": "AFFECTS",
      "statement": "Bird strikes bend or fracture fan blades.",
      "subject": "FM_fod",
      "object": "P_fan_blade",
      "confidence": 0.85,
      "source_chunk_ids": [
        "D3_c28"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL051",
      "predicate": "CAUSES",
      "statement": "Failed fuel-tank boost pumps or contamination generate debris that clogs the fuel filter.",
      "subject": "C_boost_pump_failure",
      "object": "FM_fuel_filter_clogging",
      "confidence": 0.8,
      "source_chunk_ids": [
        "D3_c29"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL052",
      "predicate": "LEADS_TO",
      "statement": "Once filters bypass and contaminant enters the fuel control, multiple-engine flameout becomes possible.",
      "subject": "FM_fuel_filter_clogging",
      "object": "FM_flameout",
      "confidence": 0.75,
      "source_chunk_ids": [
        "D3_c30"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL053",
      "predicate": "MANIFESTS_AS",
      "statement": "Severe damage can show surge, vibration, fire warning, high EGT, oil out-of-limits and rotor decay.",
      "subject": "FM_severe_engine_damage",
      "object": "SY_high_vibration",
      "confidence": 0.8,
      "source_chunk_ids": [
        "D3_c31"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL054",
      "predicate": "CAUSES",
      "statement": "Combustion heat and exposure drive hardware corrosion and oxidation distress.",
      "subject": "C_combustion_heat",
      "object": "FM_corrosion",
      "confidence": 0.7,
      "source_chunk_ids": [
        "D1_c22"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL055",
      "predicate": "CAUSES",
      "statement": "Rotor/case interference makes blade tips rub their outer shrouds, increasing clearances.",
      "subject": "C_rotor_case_interference",
      "object": "FM_blade_tip_rub",
      "confidence": 0.9,
      "source_chunk_ids": [
        "D4_c01"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL056",
      "predicate": "CAUSES",
      "statement": "Blade-tip-to-shroud rubs are the predominant cause of clearance increase.",
      "subject": "FM_blade_tip_rub",
      "object": "FM_tip_clearance_increase",
      "confidence": 0.9,
      "source_chunk_ids": [
        "D4_c02"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL057",
      "predicate": "DEGRADES",
      "statement": "Increased running clearances raise cruise specific fuel consumption.",
      "subject": "FM_tip_clearance_increase",
      "object": "PA_sfc",
      "confidence": 0.9,
      "source_chunk_ids": [
        "D4_c03"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL058",
      "predicate": "CAUSES",
      "statement": "Flight loads during take-off rotation, maneuvers, landing and thrust reversal deflect the engine, producing tip rubs.",
      "subject": "C_flight_loads",
      "object": "FM_blade_tip_rub",
      "confidence": 0.9,
      "source_chunk_ids": [
        "D4_c04"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL059",
      "predicate": "CAUSES",
      "statement": "Hot rotor reburst, a thermal transient, causes HPT blade rubs from differential thermal growth.",
      "subject": "C_hot_rotor_reburst",
      "object": "FM_blade_tip_rub",
      "confidence": 0.85,
      "source_chunk_ids": [
        "D4_c05"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL060",
      "predicate": "CAUSES",
      "statement": "Cold-section airfoil quality loss (FOD, erosion, surface roughness) is a major deterioration contributor.",
      "subject": "C_particulate_ingestion",
      "object": "FM_airfoil_erosion",
      "confidence": 0.85,
      "source_chunk_ids": [
        "D4_c06"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL061",
      "predicate": "CAUSES",
      "statement": "In the hot section, thermal distortion warps and distorts vanes.",
      "subject": "C_thermal_stress",
      "object": "FM_thermal_distortion",
      "confidence": 0.85,
      "source_chunk_ids": [
        "D4_c07"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL062",
      "predicate": "DEGRADES",
      "statement": "High- and low-pressure turbine thermal distortion contributes to long-term SFC deterioration.",
      "subject": "FM_thermal_distortion",
      "object": "PA_sfc",
      "confidence": 0.8,
      "source_chunk_ids": [
        "D4_c08"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL063",
      "predicate": "AFFECTS",
      "statement": "HPT clearance increases dominate short-term deterioration (over 90% for the CF6-6D).",
      "subject": "FM_tip_clearance_increase",
      "object": "M_hpt",
      "confidence": 0.85,
      "source_chunk_ids": [
        "D4_c09"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL064",
      "predicate": "MANIFESTS_AS",
      "statement": "Clearance-driven efficiency loss appears as rising cruise SFC.",
      "subject": "FM_tip_clearance_increase",
      "object": "SY_sfc_increase",
      "confidence": 0.8,
      "source_chunk_ids": [
        "D4_c10"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL065",
      "predicate": "RESTORES",
      "statement": "HPT repair restores roughly 0.8-0.9% cruise SFC, though ~0.2% remains unrestored.",
      "subject": "MI_performance_restoration",
      "object": "PA_sfc",
      "confidence": 0.8,
      "source_chunk_ids": [
        "D4_c11"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL066",
      "predicate": "MITIGATES",
      "statement": "Ducting compressor air onto the cases shrinks them toward the blade tips, controlling clearance.",
      "subject": "MI_clearance_control_bleed",
      "object": "FM_tip_clearance_increase",
      "confidence": 0.8,
      "source_chunk_ids": [
        "D3_c32"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL067",
      "predicate": "ENABLES",
      "statement": "PHM predicts degradation progression before catastrophic failure, enabling proactive maintenance.",
      "subject": "ME_phm",
      "object": "MI_predictive_maintenance",
      "confidence": 0.85,
      "source_chunk_ids": [
        "D2_c01"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL068",
      "predicate": "DETECTS",
      "statement": "ANN-Flux jointly predicts health state, eventual failing component(s) and RUL (AUROC/AUPR > 0.95).",
      "subject": "ME_ann_flux",
      "object": "FM_hardware_deterioration",
      "confidence": 0.85,
      "source_chunk_ids": [
        "D2_c02"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL069",
      "predicate": "SUPPORTS",
      "statement": "PCA orthogonalization markedly improves component-failure classification performance.",
      "subject": "ME_pca",
      "object": "ME_ann_flux",
      "confidence": 0.8,
      "source_chunk_ids": [
        "D2_c03"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL070",
      "predicate": "MITIGATES",
      "statement": "Predictive maintenance dispatches the right experts/resources in time and cuts reactive-maintenance cost.",
      "subject": "MI_predictive_maintenance",
      "object": "FM_severe_engine_damage",
      "confidence": 0.75,
      "source_chunk_ids": [
        "D2_c04"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL071",
      "predicate": "MODELS",
      "statement": "N-CMAPSS encodes 7 failure modes across the fan, LPC, HPC, HPT and LPT rotating subcomponents.",
      "subject": "ME_ncmapss",
      "object": "FM_hardware_deterioration",
      "confidence": 0.8,
      "source_chunk_ids": [
        "D2_c05"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL072",
      "predicate": "MODELS",
      "statement": "Symbolic regression finds interpretable algebraic relations for EGT (~3 degC error) from engine parameters.",
      "subject": "ME_symbolic_regression",
      "object": "PA_egt",
      "confidence": 0.8,
      "source_chunk_ids": [
        "D6_c01"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL073",
      "predicate": "ENABLES",
      "statement": "Advanced propulsion control and diagnostics support engine health monitoring and performance.",
      "subject": "ME_fadec",
      "object": "MI_on_condition_monitoring",
      "confidence": 0.7,
      "source_chunk_ids": [
        "D5_c01"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL074",
      "predicate": "MITIGATES",
      "statement": "Overhaul inspects, repairs and replaces worn parts to return the engine to airworthy condition.",
      "subject": "MI_overhaul",
      "object": "FM_hardware_deterioration",
      "confidence": 0.85,
      "source_chunk_ids": [
        "D7_c01"
      ],
      "extracted_by": "manual_llm_extraction"
    },
    {
      "claim_id": "CL075",
      "predicate": "DETECTS",
      "statement": "Non-destructive testing during overhaul detects unairworthy parts such as cracked airfoils.",
      "subject": "MI_ndt",
      "object": "FM_blade_cracking",
      "confidence": 0.8,
      "source_chunk_ids": [
        "D7_c02"
      ],
      "extracted_by": "manual_llm_extraction"
    }
  ],
  "relationships": [
    {
      "type": "PART_OF",
      "from": "M_fan_lpc",
      "to": "E_turbofan",
      "properties": {}
    },
    {
      "type": "PART_OF",
      "from": "M_hpc",
      "to": "E_turbofan",
      "properties": {}
    },
    {
      "type": "PART_OF",
      "from": "M_combustor",
      "to": "E_turbofan",
      "properties": {}
    },
    {
      "type": "PART_OF",
      "from": "M_hpt",
      "to": "E_turbofan",
      "properties": {}
    },
    {
      "type": "PART_OF",
      "from": "M_lpt",
      "to": "E_turbofan",
      "properties": {}
    },
    {
      "type": "PART_OF",
      "from": "M_accessory_drive",
      "to": "E_turbofan",
      "properties": {}
    },
    {
      "type": "PART_OF",
      "from": "M_core",
      "to": "E_turbofan",
      "properties": {}
    },
    {
      "type": "PART_OF",
      "from": "M_hpc",
      "to": "M_core",
      "properties": {}
    },
    {
      "type": "PART_OF",
      "from": "M_combustor",
      "to": "M_core",
      "properties": {}
    },
    {
      "type": "PART_OF",
      "from": "M_hpt",
      "to": "M_core",
      "properties": {}
    },
    {
      "type": "PART_OF",
      "from": "P_fan_blade",
      "to": "M_fan_lpc",
      "properties": {}
    },
    {
      "type": "PART_OF",
      "from": "P_fan_disk",
      "to": "M_fan_lpc",
      "properties": {}
    },
    {
      "type": "PART_OF",
      "from": "P_compressor_blade",
      "to": "M_hpc",
      "properties": {}
    },
    {
      "type": "PART_OF",
      "from": "P_compressor_vane",
      "to": "M_hpc",
      "properties": {}
    },
    {
      "type": "PART_OF",
      "from": "P_hpt_blade",
      "to": "M_hpt",
      "properties": {}
    },
    {
      "type": "PART_OF",
      "from": "P_nozzle_guide_vane",
      "to": "M_hpt",
      "properties": {}
    },
    {
      "type": "PART_OF",
      "from": "P_lpt_blade",
      "to": "M_lpt",
      "properties": {}
    },
    {
      "type": "PART_OF",
      "from": "P_fuel_nozzle",
      "to": "M_combustor",
      "properties": {}
    },
    {
      "type": "PART_OF",
      "from": "P_cooling_hole",
      "to": "M_hpt",
      "properties": {}
    },
    {
      "type": "PART_OF",
      "from": "P_shroud",
      "to": "M_hpt",
      "properties": {}
    },
    {
      "type": "PART_OF",
      "from": "P_blade_tip",
      "to": "M_hpt",
      "properties": {}
    },
    {
      "type": "IS_A",
      "from": "E_CFM56",
      "to": "E_high_bypass",
      "properties": {}
    },
    {
      "type": "IS_A",
      "from": "E_V2500",
      "to": "E_high_bypass",
      "properties": {}
    },
    {
      "type": "IS_A",
      "from": "E_JT9D",
      "to": "E_high_bypass",
      "properties": {}
    },
    {
      "type": "IS_A",
      "from": "E_CF6",
      "to": "E_high_bypass",
      "properties": {}
    },
    {
      "type": "MEASURED_BY",
      "from": "SY_high_egt",
      "to": "PA_egt",
      "properties": {}
    },
    {
      "type": "MEASURED_BY",
      "from": "SY_egt_exceedance",
      "to": "PA_egt",
      "properties": {}
    },
    {
      "type": "MEASURED_BY",
      "from": "SY_low_epr",
      "to": "PA_epr",
      "properties": {}
    },
    {
      "type": "MEASURED_BY",
      "from": "SY_epr_fluctuation",
      "to": "PA_epr",
      "properties": {}
    },
    {
      "type": "MEASURED_BY",
      "from": "SY_low_n1",
      "to": "PA_n1",
      "properties": {}
    },
    {
      "type": "MEASURED_BY",
      "from": "SY_n1_fluctuation",
      "to": "PA_n1",
      "properties": {}
    },
    {
      "type": "MEASURED_BY",
      "from": "SY_high_vibration",
      "to": "PA_vibration",
      "properties": {}
    },
    {
      "type": "MEASURED_BY",
      "from": "SY_low_oil_pressure",
      "to": "PA_oil_pressure",
      "properties": {}
    },
    {
      "type": "MEASURED_BY",
      "from": "SY_high_oil_temp",
      "to": "PA_oil_temp",
      "properties": {}
    },
    {
      "type": "MEASURED_BY",
      "from": "SY_decreasing_oil_quantity",
      "to": "PA_oil_quantity",
      "properties": {}
    },
    {
      "type": "MEASURED_BY",
      "from": "SY_rising_fuel_flow",
      "to": "PA_fuel_flow",
      "properties": {}
    },
    {
      "type": "MEASURED_BY",
      "from": "SY_high_fuel_flow",
      "to": "PA_fuel_flow",
      "properties": {}
    },
    {
      "type": "MEASURED_BY",
      "from": "SY_sfc_increase",
      "to": "PA_sfc",
      "properties": {}
    },
    {
      "type": "DEGRADES",
      "from": "FM_tip_clearance_increase",
      "to": "PA_egt_margin",
      "properties": {
        "claim_id": "CL001",
        "confidence": 0.95,
        "source_chunk_ids": [
          "D1_c01"
        ]
      }
    },
    {
      "type": "CAUSES",
      "from": "FM_tip_clearance_increase",
      "to": "FM_egt_margin_deterioration",
      "properties": {
        "claim_id": "CL002",
        "confidence": 0.9,
        "source_chunk_ids": [
          "D1_c02"
        ]
      }
    },
    {
      "type": "CAUSES",
      "from": "C_blade_tip_wear",
      "to": "FM_tip_clearance_increase",
      "properties": {
        "claim_id": "CL003",
        "confidence": 0.85,
        "source_chunk_ids": [
          "D1_c03"
        ]
      }
    },
    {
      "type": "INFLUENCES",
      "from": "OF_thrust_rating",
      "to": "FM_egt_margin_deterioration",
      "properties": {
        "claim_id": "CL004",
        "confidence": 0.9,
        "source_chunk_ids": [
          "D1_c04"
        ],
        "effect": "increases"
      }
    },
    {
      "type": "MITIGATES",
      "from": "MI_takeoff_derate",
      "to": "FM_egt_margin_deterioration",
      "properties": {
        "claim_id": "CL005",
        "confidence": 0.9,
        "source_chunk_ids": [
          "D1_c05"
        ],
        "effect": "reduces"
      }
    },
    {
      "type": "INFLUENCES",
      "from": "OF_environment",
      "to": "FM_airfoil_erosion",
      "properties": {
        "claim_id": "CL006",
        "confidence": 0.9,
        "source_chunk_ids": [
          "D1_c06"
        ],
        "effect": "increases"
      }
    },
    {
      "type": "CAUSES",
      "from": "C_particulate_ingestion",
      "to": "FM_airfoil_erosion",
      "properties": {
        "claim_ids": [
          "CL007",
          "CL060"
        ],
        "source_chunk_ids": [
          "D1_c07",
          "D4_c06"
        ],
        "confidence": 0.875,
        "merged_from_relationship_count": 2
      }
    },
    {
      "type": "CAUSES",
      "from": "C_particulate_ingestion",
      "to": "FM_blocked_cooling_holes",
      "properties": {
        "claim_id": "CL008",
        "confidence": 0.9,
        "source_chunk_ids": [
          "D1_c08"
        ]
      }
    },
    {
      "type": "RESTORES",
      "from": "MI_water_wash",
      "to": "PA_egt_margin",
      "properties": {
        "claim_id": "CL009",
        "confidence": 0.9,
        "source_chunk_ids": [
          "D1_c09"
        ]
      }
    },
    {
      "type": "MITIGATES",
      "from": "MI_water_wash",
      "to": "FM_egt_margin_deterioration",
      "properties": {
        "claim_id": "CL010",
        "confidence": 0.85,
        "source_chunk_ids": [
          "D1_c10"
        ]
      }
    },
    {
      "type": "MITIGATES",
      "from": "MI_performance_restoration",
      "to": "FM_hardware_deterioration",
      "properties": {
        "claim_id": "CL011",
        "confidence": 0.9,
        "source_chunk_ids": [
          "D1_c11"
        ]
      }
    },
    {
      "type": "DETECTS",
      "from": "MI_borescope_inspection",
      "to": "FM_blade_cracking",
      "properties": {
        "claim_id": "CL012",
        "confidence": 0.9,
        "source_chunk_ids": [
          "D1_c12"
        ]
      }
    },
    {
      "type": "DETECTS",
      "from": "MI_on_condition_monitoring",
      "to": "FM_egt_margin_deterioration",
      "properties": {
        "claim_id": "CL013",
        "confidence": 0.85,
        "source_chunk_ids": [
          "D1_c13"
        ]
      }
    },
    {
      "type": "AFFECTS",
      "from": "FM_hardware_deterioration",
      "to": "P_hpt_blade",
      "properties": {
        "claim_id": "CL014",
        "confidence": 0.85,
        "source_chunk_ids": [
          "D1_c14"
        ]
      }
    },
    {
      "type": "CAUSES",
      "from": "C_fod_ingestion",
      "to": "FM_fod",
      "properties": {
        "claim_id": "CL015",
        "confidence": 0.95,
        "source_chunk_ids": [
          "D1_c15"
        ]
      }
    },
    {
      "type": "INFLUENCES",
      "from": "OF_short_haul",
      "to": "FM_llp_expiry",
      "properties": {
        "claim_id": "CL016",
        "confidence": 0.85,
        "source_chunk_ids": [
          "D1_c16"
        ],
        "effect": "increases"
      }
    },
    {
      "type": "MITIGATES",
      "from": "MI_llp_replacement",
      "to": "FM_llp_expiry",
      "properties": {
        "claim_id": "CL017",
        "confidence": 0.9,
        "source_chunk_ids": [
          "D1_c17"
        ]
      }
    },
    {
      "type": "INFLUENCES",
      "from": "OF_flight_length",
      "to": "FM_egt_margin_deterioration",
      "properties": {
        "claim_id": "CL018",
        "confidence": 0.9,
        "source_chunk_ids": [
          "D1_c18"
        ],
        "effect": "increases_when_short"
      }
    },
    {
      "type": "INFLUENCES",
      "from": "OF_oat",
      "to": "FM_egt_margin_deterioration",
      "properties": {
        "claim_id": "CL019",
        "confidence": 0.9,
        "source_chunk_ids": [
          "D1_c19"
        ],
        "effect": "increases"
      }
    },
    {
      "type": "INFLUENCES",
      "from": "OF_engine_age",
      "to": "FM_hardware_deterioration",
      "properties": {
        "claim_id": "CL020",
        "confidence": 0.85,
        "source_chunk_ids": [
          "D1_c20"
        ],
        "effect": "increases"
      }
    },
    {
      "type": "MANIFESTS_AS",
      "from": "FM_egt_margin_deterioration",
      "to": "SY_high_egt",
      "properties": {
        "claim_id": "CL021",
        "confidence": 0.85,
        "source_chunk_ids": [
          "D1_c21"
        ]
      }
    },
    {
      "type": "CAUSES",
      "from": "C_compressor_airfoil_stall",
      "to": "FM_compressor_surge",
      "properties": {
        "claim_id": "CL022",
        "confidence": 0.9,
        "source_chunk_ids": [
          "D3_c01"
        ]
      }
    },
    {
      "type": "CAUSES",
      "from": "C_fod_ingestion",
      "to": "FM_compressor_surge",
      "properties": {
        "claim_id": "CL023",
        "confidence": 0.85,
        "source_chunk_ids": [
          "D3_c02"
        ]
      }
    },
    {
      "type": "MANIFESTS_AS",
      "from": "FM_compressor_surge",
      "to": "SY_loud_bang",
      "properties": {
        "claim_id": "CL024",
        "confidence": 0.95,
        "source_chunk_ids": [
          "D3_c03"
        ]
      }
    },
    {
      "type": "MANIFESTS_AS",
      "from": "FM_compressor_surge",
      "to": "SY_visible_flame",
      "properties": {
        "claim_id": "CL025",
        "confidence": 0.85,
        "source_chunk_ids": [
          "D3_c04"
        ]
      }
    },
    {
      "type": "MANIFESTS_AS",
      "from": "FM_compressor_surge",
      "to": "SY_high_egt",
      "properties": {
        "claim_id": "CL026",
        "confidence": 0.8,
        "source_chunk_ids": [
          "D3_c05"
        ]
      }
    },
    {
      "type": "MITIGATES",
      "from": "MI_thrust_reduction",
      "to": "FM_compressor_surge",
      "properties": {
        "claim_id": "CL027",
        "confidence": 0.9,
        "source_chunk_ids": [
          "D3_c06"
        ]
      }
    },
    {
      "type": "LEADS_TO",
      "from": "FM_compressor_surge",
      "to": "FM_severe_engine_damage",
      "properties": {
        "claim_id": "CL028",
        "confidence": 0.85,
        "source_chunk_ids": [
          "D3_c07"
        ]
      }
    },
    {
      "type": "CAUSES",
      "from": "C_fuel_starvation",
      "to": "FM_flameout",
      "properties": {
        "claim_id": "CL029",
        "confidence": 0.9,
        "source_chunk_ids": [
          "D3_c08"
        ]
      }
    },
    {
      "type": "LEADS_TO",
      "from": "FM_compressor_surge",
      "to": "FM_flameout",
      "properties": {
        "claim_id": "CL030",
        "confidence": 0.8,
        "source_chunk_ids": [
          "D3_c09"
        ]
      }
    },
    {
      "type": "MANIFESTS_AS",
      "from": "FM_flameout",
      "to": "SY_low_epr",
      "properties": {
        "claim_id": "CL031",
        "confidence": 0.9,
        "source_chunk_ids": [
          "D3_c10"
        ]
      }
    },
    {
      "type": "MANIFESTS_AS",
      "from": "FM_flameout",
      "to": "SY_low_oil_pressure",
      "properties": {
        "claim_id": "CL032",
        "confidence": 0.8,
        "source_chunk_ids": [
          "D3_c11"
        ]
      }
    },
    {
      "type": "MITIGATES",
      "from": "MI_continuous_ignition",
      "to": "FM_flameout",
      "properties": {
        "claim_id": "CL033",
        "confidence": 0.85,
        "source_chunk_ids": [
          "D3_c12"
        ]
      }
    },
    {
      "type": "INDICATES",
      "from": "SY_low_epr",
      "to": "FM_flameout",
      "properties": {
        "claim_id": "CL034",
        "confidence": 0.85,
        "source_chunk_ids": [
          "D3_c13"
        ]
      }
    },
    {
      "type": "INDICATES",
      "from": "SY_epr_fluctuation",
      "to": "FM_compressor_surge",
      "properties": {
        "claim_id": "CL035",
        "confidence": 0.85,
        "source_chunk_ids": [
          "D3_c14"
        ]
      }
    },
    {
      "type": "INDICATES",
      "from": "SY_egt_exceedance",
      "to": "FM_severe_engine_damage",
      "properties": {
        "claim_id": "CL036",
        "confidence": 0.8,
        "source_chunk_ids": [
          "D3_c15"
        ]
      }
    },
    {
      "type": "INDICATES",
      "from": "SY_high_vibration",
      "to": "FM_fan_unbalance",
      "properties": {
        "claim_id": "CL037",
        "confidence": 0.8,
        "source_chunk_ids": [
          "D3_c16"
        ]
      }
    },
    {
      "type": "INDICATES",
      "from": "SY_high_vibration",
      "to": "FM_bearing_failure",
      "properties": {
        "claim_id": "CL038",
        "confidence": 0.8,
        "source_chunk_ids": [
          "D3_c17"
        ]
      }
    },
    {
      "type": "MANIFESTS_AS",
      "from": "FM_bearing_failure",
      "to": "SY_high_oil_temp",
      "properties": {
        "claim_id": "CL039",
        "confidence": 0.85,
        "source_chunk_ids": [
          "D3_c17"
        ]
      }
    },
    {
      "type": "CAUSES",
      "from": "C_bearing_distress",
      "to": "FM_bearing_failure",
      "properties": {
        "claim_id": "CL040",
        "confidence": 0.75,
        "source_chunk_ids": [
          "D3_c18"
        ]
      }
    },
    {
      "type": "MANIFESTS_AS",
      "from": "FM_oil_leak_or_oil_loss",
      "to": "SY_decreasing_oil_quantity",
      "properties": {
        "claim_id": "CL041",
        "confidence": 0.85,
        "source_chunk_ids": [
          "D3_c19"
        ]
      }
    },
    {
      "type": "INDICATES",
      "from": "SY_oil_filter_bypass",
      "to": "FM_bearing_failure",
      "properties": {
        "claim_id": "CL042",
        "confidence": 0.75,
        "source_chunk_ids": [
          "D3_c20"
        ]
      }
    },
    {
      "type": "CAUSES",
      "from": "C_fuel_puddling",
      "to": "FM_tailpipe_fire",
      "properties": {
        "claim_id": "CL043",
        "confidence": 0.9,
        "source_chunk_ids": [
          "D3_c21"
        ]
      }
    },
    {
      "type": "MITIGATES",
      "from": "MI_dry_motoring",
      "to": "FM_tailpipe_fire",
      "properties": {
        "claim_id": "CL044",
        "confidence": 0.85,
        "source_chunk_ids": [
          "D3_c22"
        ]
      }
    },
    {
      "type": "MANIFESTS_AS",
      "from": "FM_engine_fire",
      "to": "SY_fire_warning",
      "properties": {
        "claim_id": "CL045",
        "confidence": 0.85,
        "source_chunk_ids": [
          "D3_c23"
        ]
      }
    },
    {
      "type": "MITIGATES",
      "from": "MI_engine_shutdown",
      "to": "FM_engine_fire",
      "properties": {
        "claim_id": "CL046",
        "confidence": 0.85,
        "source_chunk_ids": [
          "D3_c24"
        ]
      }
    },
    {
      "type": "MANIFESTS_AS",
      "from": "FM_hot_start",
      "to": "SY_high_egt",
      "properties": {
        "claim_id": "CL047",
        "confidence": 0.85,
        "source_chunk_ids": [
          "D3_c25"
        ]
      }
    },
    {
      "type": "CAUSES",
      "from": "C_fod_ingestion",
      "to": "FM_fan_unbalance",
      "properties": {
        "claim_id": "CL048",
        "confidence": 0.8,
        "source_chunk_ids": [
          "D3_c26"
        ]
      }
    },
    {
      "type": "LEADS_TO",
      "from": "FM_fod",
      "to": "FM_compressor_surge",
      "properties": {
        "claim_id": "CL049",
        "confidence": 0.8,
        "source_chunk_ids": [
          "D3_c27"
        ]
      }
    },
    {
      "type": "AFFECTS",
      "from": "FM_fod",
      "to": "P_fan_blade",
      "properties": {
        "claim_id": "CL050",
        "confidence": 0.85,
        "source_chunk_ids": [
          "D3_c28"
        ]
      }
    },
    {
      "type": "CAUSES",
      "from": "C_boost_pump_failure",
      "to": "FM_fuel_filter_clogging",
      "properties": {
        "claim_id": "CL051",
        "confidence": 0.8,
        "source_chunk_ids": [
          "D3_c29"
        ]
      }
    },
    {
      "type": "LEADS_TO",
      "from": "FM_fuel_filter_clogging",
      "to": "FM_flameout",
      "properties": {
        "claim_id": "CL052",
        "confidence": 0.75,
        "source_chunk_ids": [
          "D3_c30"
        ]
      }
    },
    {
      "type": "MANIFESTS_AS",
      "from": "FM_severe_engine_damage",
      "to": "SY_high_vibration",
      "properties": {
        "claim_id": "CL053",
        "confidence": 0.8,
        "source_chunk_ids": [
          "D3_c31"
        ]
      }
    },
    {
      "type": "CAUSES",
      "from": "C_combustion_heat",
      "to": "FM_corrosion",
      "properties": {
        "claim_id": "CL054",
        "confidence": 0.7,
        "source_chunk_ids": [
          "D1_c22"
        ]
      }
    },
    {
      "type": "CAUSES",
      "from": "C_rotor_case_interference",
      "to": "FM_blade_tip_rub",
      "properties": {
        "claim_id": "CL055",
        "confidence": 0.9,
        "source_chunk_ids": [
          "D4_c01"
        ]
      }
    },
    {
      "type": "CAUSES",
      "from": "FM_blade_tip_rub",
      "to": "FM_tip_clearance_increase",
      "properties": {
        "claim_id": "CL056",
        "confidence": 0.9,
        "source_chunk_ids": [
          "D4_c02"
        ]
      }
    },
    {
      "type": "DEGRADES",
      "from": "FM_tip_clearance_increase",
      "to": "PA_sfc",
      "properties": {
        "claim_id": "CL057",
        "confidence": 0.9,
        "source_chunk_ids": [
          "D4_c03"
        ]
      }
    },
    {
      "type": "CAUSES",
      "from": "C_flight_loads",
      "to": "FM_blade_tip_rub",
      "properties": {
        "claim_id": "CL058",
        "confidence": 0.9,
        "source_chunk_ids": [
          "D4_c04"
        ]
      }
    },
    {
      "type": "CAUSES",
      "from": "C_hot_rotor_reburst",
      "to": "FM_blade_tip_rub",
      "properties": {
        "claim_id": "CL059",
        "confidence": 0.85,
        "source_chunk_ids": [
          "D4_c05"
        ]
      }
    },
    {
      "type": "CAUSES",
      "from": "C_thermal_stress",
      "to": "FM_thermal_distortion",
      "properties": {
        "claim_id": "CL061",
        "confidence": 0.85,
        "source_chunk_ids": [
          "D4_c07"
        ]
      }
    },
    {
      "type": "DEGRADES",
      "from": "FM_thermal_distortion",
      "to": "PA_sfc",
      "properties": {
        "claim_id": "CL062",
        "confidence": 0.8,
        "source_chunk_ids": [
          "D4_c08"
        ]
      }
    },
    {
      "type": "AFFECTS",
      "from": "FM_tip_clearance_increase",
      "to": "M_hpt",
      "properties": {
        "claim_id": "CL063",
        "confidence": 0.85,
        "source_chunk_ids": [
          "D4_c09"
        ]
      }
    },
    {
      "type": "MANIFESTS_AS",
      "from": "FM_tip_clearance_increase",
      "to": "SY_sfc_increase",
      "properties": {
        "claim_id": "CL064",
        "confidence": 0.8,
        "source_chunk_ids": [
          "D4_c10"
        ]
      }
    },
    {
      "type": "RESTORES",
      "from": "MI_performance_restoration",
      "to": "PA_sfc",
      "properties": {
        "claim_id": "CL065",
        "confidence": 0.8,
        "source_chunk_ids": [
          "D4_c11"
        ]
      }
    },
    {
      "type": "MITIGATES",
      "from": "MI_clearance_control_bleed",
      "to": "FM_tip_clearance_increase",
      "properties": {
        "claim_id": "CL066",
        "confidence": 0.8,
        "source_chunk_ids": [
          "D3_c32"
        ]
      }
    },
    {
      "type": "ENABLES",
      "from": "ME_phm",
      "to": "MI_predictive_maintenance",
      "properties": {
        "claim_id": "CL067",
        "confidence": 0.85,
        "source_chunk_ids": [
          "D2_c01"
        ]
      }
    },
    {
      "type": "DETECTS",
      "from": "ME_ann_flux",
      "to": "FM_hardware_deterioration",
      "properties": {
        "claim_id": "CL068",
        "confidence": 0.85,
        "source_chunk_ids": [
          "D2_c02"
        ]
      }
    },
    {
      "type": "SUPPORTS",
      "from": "ME_pca",
      "to": "ME_ann_flux",
      "properties": {
        "claim_id": "CL069",
        "confidence": 0.8,
        "source_chunk_ids": [
          "D2_c03"
        ]
      }
    },
    {
      "type": "MITIGATES",
      "from": "MI_predictive_maintenance",
      "to": "FM_severe_engine_damage",
      "properties": {
        "claim_id": "CL070",
        "confidence": 0.75,
        "source_chunk_ids": [
          "D2_c04"
        ]
      }
    },
    {
      "type": "MODELS",
      "from": "ME_ncmapss",
      "to": "FM_hardware_deterioration",
      "properties": {
        "claim_id": "CL071",
        "confidence": 0.8,
        "source_chunk_ids": [
          "D2_c05"
        ]
      }
    },
    {
      "type": "MODELS",
      "from": "ME_symbolic_regression",
      "to": "PA_egt",
      "properties": {
        "claim_id": "CL072",
        "confidence": 0.8,
        "source_chunk_ids": [
          "D6_c01"
        ]
      }
    },
    {
      "type": "ENABLES",
      "from": "ME_fadec",
      "to": "MI_on_condition_monitoring",
      "properties": {
        "claim_id": "CL073",
        "confidence": 0.7,
        "source_chunk_ids": [
          "D5_c01"
        ]
      }
    },
    {
      "type": "MITIGATES",
      "from": "MI_overhaul",
      "to": "FM_hardware_deterioration",
      "properties": {
        "claim_id": "CL074",
        "confidence": 0.85,
        "source_chunk_ids": [
          "D7_c01"
        ]
      }
    },
    {
      "type": "DETECTS",
      "from": "MI_ndt",
      "to": "FM_blade_cracking",
      "properties": {
        "claim_id": "CL075",
        "confidence": 0.8,
        "source_chunk_ids": [
          "D7_c02"
        ]
      }
    }
  ],
  "mentioned_in": [
    {
      "type": "MENTIONED_IN",
      "from": "C_bearing_distress",
      "to": "D3_c18",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "C_blade_tip_wear",
      "to": "D1_c03",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "C_boost_pump_failure",
      "to": "D3_c29",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "C_combustion_heat",
      "to": "D1_c22",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "C_compressor_airfoil_stall",
      "to": "D3_c01",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "C_flight_loads",
      "to": "D4_c04",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "C_fod_ingestion",
      "to": "D1_c15",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "C_fod_ingestion",
      "to": "D3_c02",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "C_fod_ingestion",
      "to": "D3_c26",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "C_fuel_puddling",
      "to": "D3_c21",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "C_fuel_starvation",
      "to": "D3_c08",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "C_hot_rotor_reburst",
      "to": "D4_c05",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "C_particulate_ingestion",
      "to": "D1_c07",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "C_particulate_ingestion",
      "to": "D1_c08",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "C_particulate_ingestion",
      "to": "D4_c06",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "C_rotor_case_interference",
      "to": "D4_c01",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "C_thermal_stress",
      "to": "D4_c07",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_airfoil_erosion",
      "to": "D1_c06",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_airfoil_erosion",
      "to": "D1_c07",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_airfoil_erosion",
      "to": "D4_c06",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_bearing_failure",
      "to": "D3_c17",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_bearing_failure",
      "to": "D3_c18",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_bearing_failure",
      "to": "D3_c20",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_blade_cracking",
      "to": "D1_c12",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_blade_cracking",
      "to": "D7_c02",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_blade_tip_rub",
      "to": "D4_c01",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_blade_tip_rub",
      "to": "D4_c02",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_blade_tip_rub",
      "to": "D4_c04",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_blade_tip_rub",
      "to": "D4_c05",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_blocked_cooling_holes",
      "to": "D1_c08",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_compressor_surge",
      "to": "D3_c01",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_compressor_surge",
      "to": "D3_c02",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_compressor_surge",
      "to": "D3_c03",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_compressor_surge",
      "to": "D3_c04",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_compressor_surge",
      "to": "D3_c05",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_compressor_surge",
      "to": "D3_c06",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_compressor_surge",
      "to": "D3_c07",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_compressor_surge",
      "to": "D3_c09",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_compressor_surge",
      "to": "D3_c14",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_compressor_surge",
      "to": "D3_c27",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_corrosion",
      "to": "D1_c22",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_egt_margin_deterioration",
      "to": "D1_c02",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_egt_margin_deterioration",
      "to": "D1_c04",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_egt_margin_deterioration",
      "to": "D1_c05",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_egt_margin_deterioration",
      "to": "D1_c10",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_egt_margin_deterioration",
      "to": "D1_c13",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_egt_margin_deterioration",
      "to": "D1_c18",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_egt_margin_deterioration",
      "to": "D1_c19",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_egt_margin_deterioration",
      "to": "D1_c21",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_engine_fire",
      "to": "D3_c23",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_engine_fire",
      "to": "D3_c24",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_fan_unbalance",
      "to": "D3_c16",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_fan_unbalance",
      "to": "D3_c26",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_flameout",
      "to": "D3_c08",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_flameout",
      "to": "D3_c09",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_flameout",
      "to": "D3_c10",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_flameout",
      "to": "D3_c11",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_flameout",
      "to": "D3_c12",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_flameout",
      "to": "D3_c13",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_flameout",
      "to": "D3_c30",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_fod",
      "to": "D1_c15",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_fod",
      "to": "D3_c27",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_fod",
      "to": "D3_c28",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_fuel_filter_clogging",
      "to": "D3_c29",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_fuel_filter_clogging",
      "to": "D3_c30",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_hardware_deterioration",
      "to": "D1_c11",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_hardware_deterioration",
      "to": "D1_c14",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_hardware_deterioration",
      "to": "D1_c20",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_hardware_deterioration",
      "to": "D2_c02",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_hardware_deterioration",
      "to": "D2_c05",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_hardware_deterioration",
      "to": "D7_c01",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_oil_leak_or_oil_loss",
      "to": "D3_c19",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_hot_start",
      "to": "D3_c25",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_llp_expiry",
      "to": "D1_c16",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_llp_expiry",
      "to": "D1_c17",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_severe_engine_damage",
      "to": "D2_c04",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_severe_engine_damage",
      "to": "D3_c07",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_severe_engine_damage",
      "to": "D3_c15",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_severe_engine_damage",
      "to": "D3_c31",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_tailpipe_fire",
      "to": "D3_c21",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_tailpipe_fire",
      "to": "D3_c22",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_thermal_distortion",
      "to": "D4_c07",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_thermal_distortion",
      "to": "D4_c08",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_tip_clearance_increase",
      "to": "D1_c01",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_tip_clearance_increase",
      "to": "D1_c02",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_tip_clearance_increase",
      "to": "D1_c03",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_tip_clearance_increase",
      "to": "D3_c32",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_tip_clearance_increase",
      "to": "D4_c02",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_tip_clearance_increase",
      "to": "D4_c03",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_tip_clearance_increase",
      "to": "D4_c09",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "FM_tip_clearance_increase",
      "to": "D4_c10",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "ME_ann_flux",
      "to": "D2_c02",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "ME_ann_flux",
      "to": "D2_c03",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "ME_fadec",
      "to": "D5_c01",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "ME_ncmapss",
      "to": "D2_c05",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "ME_pca",
      "to": "D2_c03",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "ME_phm",
      "to": "D2_c01",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "ME_symbolic_regression",
      "to": "D6_c01",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "MI_borescope_inspection",
      "to": "D1_c12",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "MI_clearance_control_bleed",
      "to": "D3_c32",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "MI_continuous_ignition",
      "to": "D3_c12",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "MI_dry_motoring",
      "to": "D3_c22",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "MI_engine_shutdown",
      "to": "D3_c24",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "MI_llp_replacement",
      "to": "D1_c17",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "MI_ndt",
      "to": "D7_c02",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "MI_on_condition_monitoring",
      "to": "D1_c13",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "MI_on_condition_monitoring",
      "to": "D5_c01",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "MI_overhaul",
      "to": "D7_c01",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "MI_performance_restoration",
      "to": "D1_c11",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "MI_performance_restoration",
      "to": "D4_c11",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "MI_predictive_maintenance",
      "to": "D2_c01",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "MI_predictive_maintenance",
      "to": "D2_c04",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "MI_takeoff_derate",
      "to": "D1_c05",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "MI_thrust_reduction",
      "to": "D3_c06",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "MI_water_wash",
      "to": "D1_c09",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "MI_water_wash",
      "to": "D1_c10",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "M_hpt",
      "to": "D4_c09",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "OF_engine_age",
      "to": "D1_c20",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "OF_environment",
      "to": "D1_c06",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "OF_flight_length",
      "to": "D1_c18",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "OF_oat",
      "to": "D1_c19",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "OF_short_haul",
      "to": "D1_c16",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "OF_thrust_rating",
      "to": "D1_c04",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "PA_egt",
      "to": "D6_c01",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "PA_egt_margin",
      "to": "D1_c01",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "PA_egt_margin",
      "to": "D1_c09",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "PA_sfc",
      "to": "D4_c03",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "PA_sfc",
      "to": "D4_c08",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "PA_sfc",
      "to": "D4_c11",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "P_fan_blade",
      "to": "D3_c28",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "P_hpt_blade",
      "to": "D1_c14",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "SY_decreasing_oil_quantity",
      "to": "D3_c19",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "SY_egt_exceedance",
      "to": "D3_c15",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "SY_epr_fluctuation",
      "to": "D3_c14",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "SY_fire_warning",
      "to": "D3_c23",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "SY_high_egt",
      "to": "D1_c21",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "SY_high_egt",
      "to": "D3_c05",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "SY_high_egt",
      "to": "D3_c25",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "SY_high_oil_temp",
      "to": "D3_c17",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "SY_high_vibration",
      "to": "D3_c16",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "SY_high_vibration",
      "to": "D3_c17",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "SY_high_vibration",
      "to": "D3_c31",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "SY_loud_bang",
      "to": "D3_c03",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "SY_low_epr",
      "to": "D3_c10",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "SY_low_epr",
      "to": "D3_c13",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "SY_low_oil_pressure",
      "to": "D3_c11",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "SY_oil_filter_bypass",
      "to": "D3_c20",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "SY_sfc_increase",
      "to": "D4_c10",
      "properties": {}
    },
    {
      "type": "MENTIONED_IN",
      "from": "SY_visible_flame",
      "to": "D3_c04",
      "properties": {}
    }
  ]
}