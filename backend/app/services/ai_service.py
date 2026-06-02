from app.services.question_quality import is_valid_question

# ── Document content (trimmed for token efficiency) ─────────────────────────

RESCUE_CONTENT = """Basic Rescue Course - Rescue 1122 Punjab Emergency Service Training Materials:

ROPES: Parts of rope: Working End (tied to anchor), Running End (for hoisting), Standing Part (between ends). Manufacturing: Kern (internal fiber, 70% strength) and Mantle (outer cover, 30% strength).
Types: Utility Rope (natural fibers, equipment securing only, NOT life safety). Life Safety Rope (11mm static kernmantle, inorganic fibers - polypropylene/polyester/polyethylene).
Life safety types: Static Rope (low-stretch, 2-3% elongation under body weight, max 20% at break, used for rappelling/rescue) and Dynamic Rope (high-stretch up to 60%, rock climbing only).
Rope care BEFORE: remove kinks, secure ends with stopper, inspect thoroughly. DURING: no dragging on ground, no wet places, no sharp edges, avoid heat/grease/oil/chemicals, no walking on rope. AFTER: inspect, fold after removing kinks, no knots left (reduces strength), no drying near fire, store in ventilated dry place off floor away from sunlight and moisture.
Inspection: Visual checks - discoloration (chemical contamination), melting (heat damage), white filaments (sheath damaged), size uniformity changes (mechanical impact), excessive abrasion. By feel: soft spots, hard spots indicate core damage.

KNOTS: Stopper Knot (prevents rope slipping). Clove Hitch (quick anchor). Reef Knot (joining same diameter ropes). Slip Knot (adjustable loop). Sheet Bend (joining different diameter ropes). Figure of Eight on Bight (strong loop, mountaineering standard). Round Turn with Two Half Hitches (securing to post/ring). Prussic Knot (friction hitch for ascending). Bowline (non-slipping loop, most common rescue knot). Double Bowline (extra safety). Triple Bowline (three loops rescue harness). Long Tail Bowline (extra security tail).

PPE: Basic PPE: safety helmet, eye protection, ear protection, dust mask, safety steel-toe boots, work gloves, high-visibility vest. Advanced: SCBA, chemical suits, flash protection.
Body areas: Hand Care (leather/rubber/Kevlar gloves). Head Care (helmets must meet safety standards, never use damaged). Foot Care (steel-toe, puncture-resistant soles). Breathing (dust masks for dust, SCBA for toxic/oxygen-deficient - cylinder duration 30-45 minutes). Eyes (chemical splash vs impact protection). Ears (NRR rated, ear muffs vs ear plugs). Height safety (fall arrest, harnesses, lanyards, anchor points).

ROPE RESCUE TECHNIQUES: Five techniques: Rappelling (descending with friction device), Ascending (mechanical ascenders/prussic knots), Lowering (belay system), Hauling (mechanical advantage pulley systems), Belay (safety backup protecting load).
Equipment: kernmantle rope, harness, locking carabiner, descender/figure-eight, ascender/jumar, prussic loops, pulley, anchor plate, rescue stretcher, helmet.

VEHICLE EXTRICATION: Scene safety first - control traffic, fuel spills, fire hazards. Stabilization with cribbing and wedges before any entry. Tools: hydraulic spreader (jaws of life), hydraulic cutter, ram, reciprocating saw, glass management tool. Spinal precautions throughout.

DISASTER RESPONSE: START triage: Red=immediate (life threatening, treatable), Yellow=delayed (serious but stable), Green=minor (walking wounded), Black=deceased/unsurvivable.
ICS: Incident Commander at top, four sections: Operations, Planning, Logistics, Finance/Admin. Span of control: 3-7 subordinates (optimal 5). NIMS principles."""

FIRE_CONTENT = """Firefighting & Prevention Course - Rescue 1122 Training Materials (3rd Edition 2020):

FIRE CHEMISTRY: Fire Triangle: Fuel, Heat, Oxygen. Fire Tetrahedron adds chain reaction.
Fire Classes: A=ordinary combustibles (wood/paper/cloth/rubber/plastics) water effective. B=flammable liquids/gases (petrol/oil/paint/LPG) foam/CO2/dry powder. C=electrical equipment CO2 or dry powder NEVER water. D=combustible metals (magnesium/sodium/potassium) special dry powder. F=cooking oils/fats wet chemical extinguisher.
Combustion terms: Flash point (liquid produces enough vapour to ignite). Fire point (sustained combustion occurs). Autoignition (ignites without external flame). Backdraft (oxygen suddenly enters depleted hot fire - explosive). Flashover (rapid all-material ignition at 500-600°C).

FIRE EXTINGUISHERS: Water (red) Class A only. Foam (cream) Class A and B. CO2 (black) Class B and C electrical. Dry Powder/ABC (blue/red) Class A B C. Wet Chemical (yellow) Class F. Operating: water/foam 1-2m, CO2 1m minimum from live electrical.

FIRE HOSES AND PUMP: Delivery hose (63mm, 70mm). Suction hose (rigid, pump intake from static water). Hose reel (25mm semi-rigid first attack). Fire pump centrifugal type. Minimum hydrant pressure: 1.7 bar (25 psi) residual under flow. Appliance flow rates: 900-2000 L/min. Primer needed for drafting from static water.

FOAM: AFFF (Aqueous Film Forming Foam), Protein foam, Fluoroprotein. Expansion rates: low (up to 20:1), medium (20-200:1), high (200-1000:1).

SCBA: Open circuit positive pressure preferred. Components: facepiece, demand valve, pressure reducer, cylinder (steel/composite), harness/backplate, pressure gauge. Cylinder pressure: 300 bar. Duration: 30-45 minutes at normal work rate. Donning time: under 60 seconds trained firefighter. Buddy system mandatory. DSU (Distress Signal Unit) activates after 30 seconds motionless. NEVER enter alone.

FIRE LADDERS: Single (up to 4m), Extension (7-15m), Hook (internal use), Aerial/TL (truck mounted, 30-60m).

WATER SUPPLY: External fire hydrant - pillar type (above ground), underground (sluice valve). Hydrant outlets: 63mm and 38mm.

BUILDING PROTECTION: Sprinkler types: wet pipe (always water in pipes), dry pipe (air pressure, cold storage), pre-action (dual trigger), deluge (open heads). Sprinkler activation temperature: standard 68°C (red), intermediate 79°C (yellow). Detectors: ionisation (fast flaming fires), optical (slow smouldering), heat (rate of rise or fixed temperature), beam (large areas), aspirating systems.

ICS: Command staff: Incident Commander, Safety Officer, Public Information Officer, Liaison Officer. General staff: Operations, Planning, Logistics, Finance/Admin Section Chiefs.
Emergency response levels: Level 1 (routine, 1-2 units), Level 2 (moderate, multiple units), Level 3 (major incident, full response, mutual aid), Level 4 (disaster, provincial response).

FIRE RISK ASSESSMENT: Step 1: Identify fire hazards. Step 2: Identify people at risk. Step 3: Evaluate, remove or reduce risks. Step 4: Record, plan, instruct, inform, train. Step 5: Review and update. Risk matrix: likelihood x severity = risk rating.

FIRE OPERATIONS: Ventilation: horizontal (windows/doors), vertical (roof vents/skylights), hydraulic (water curtains). Forcible entry tools: halligan bar, axe, bolt cutters, saw. Size-up acronym: RECEO (Rescue, Exposure, Confinement, Extinguishment, Overhaul). Search: primary (rapid, life safety) and secondary (thorough). Right-hand or left-hand search pattern.

REPAIR AND MAINTENANCE: Regular inspection of all fire appliances and equipment. SCBA cylinder testing every 5 years. Fire hose annual pressure testing. PPE inspection before and after each use."""

BUILDING_CONTENT = """Punjab Community Safety Buildings Regulations 2022:

EMERGENCY EXITS AND STAIRCASES: Minimum two exit staircases (one may be external). After every 6,000 sq ft additional exit staircase per floor required. Maximum travel distance to exit staircase: 100 feet. Exit doors: hinge type opening outwards, minimum one-hour fire rating, headroom 80 inches, width 3 feet. Public assembly: exits increase per occupancy load per Code. Buildings above 100 feet: refuge areas on periphery or cantilever projection. Illumination: uninterrupted power minimum 90 minutes. Steps: round edges, minimum 11 inch tread, maximum 7 inch riser.

EXIT SIGNS: Illuminated exit signs with emergency lights in each corridor. EXIT in capital letters not less than 6 inches height. Visible from any direction. Placed along entire evacuation path.

HYDRANT SYSTEMS: External fire hydrant - pillar type, red colour, two outlets 2.5 inch diameter instantaneous couplings. Not more than 12 feet from fire rescue road. Minimum 5 feet clear space in front of each hydrant. Standpipe on each floor: 2.5 inch landing valves, instantaneous couplings, minimum 7 bar pressure. Connected to 100 feet long 1.5 inch delivery hose and nozzle OR 1 inch non-collapsible hose reel in hose cabinet near each exit. Systems separate from normal water supply. Electric pump plus backup pump (operational during power failure). Buildings up to 100 feet: independent overhead tank 7,500 gallons. Buildings above 100 feet: internal overhead tank 15,000 gallons AND underground tank 30,000 gallons.

AUTOMATIC SPRINKLER: Installed in all buildings. All internal car parks below ground must have sprinkler coverage.

FIRE ALARM: Automatic fire alarm and detection in all areas connected to central control panel with uninterrupted power supply. Manual fire alarm boxes on all floors within 60 inches of exit doorway, connected to audible AND flasher fire alarms.

FIRE EXTINGUISHERS: At least one multipurpose ABC dry chemical powder minimum 12 pounds per 2,000 sq ft of floor area. Maximum travel distance: 75 feet (general areas), 30 feet (combustible cooking or hazardous areas). Extinguishers up to 40 pounds: top not more than 5 feet above floor. Extinguishers over 40 pounds: top not more than 3.5 feet, bottom at least 4 inches above floor.

FIRST AID AND AED: First aid box on each floor containing: triangular bandages, crepe bandages, cotton bandages, sterilized gauze pieces, cotton roll, antiseptic solution, normal saline, scissors, sticking tape, antibacterial cream, latex gloves, face mask. Automated External Defibrillator (AED) with minimum two spare pads in the building.

HVAC: Fire dampers in HVAC ducts. Insulation of ducts must be fire retardant material.

GENERAL SAFETY: All ceiling, paneling, insulation, ducting, flooring, cladding: fire retardant. Inter-floor communication separated by fire retardant material. No bulk storage of inflammable liquids or explosive substances in basements. No loose hanging wires or loose electrical connections. No protruding rods or sharp edges. Emergency fire lifts, ramps, disability evacuation as per Code.

ACCESS: Buildings only on roads minimum 30 feet wide. No billboards or grills blocking access to 3rd floor. Outdoor wires must not create overhead obstruction.

EVACUATION PLANS AND DRILLS: Evacuation plans with floor number displayed near entrances and exits. Emergency numbers on all floors. Designated assembly areas earmarked. Evacuation drills biannual basis (twice per year). Buildings above 100 feet: emergency command center.

SAFETY MANAGER FUNCTIONS: Identify and assess hazards through regular inspections. Manage risks. Implement safety measures. Prepare emergency action plan. Establish emergency response teams and ensure safe evacuation. Conduct training for occupants and response teams. Ensure functioning of life safety and firefighting equipment. Conduct evacuation and fire drills biannually. Documentation of all activities. Liaise with local Rescue Station.

CERTIFICATE PROCEDURE: Application via official Service website. Includes: owner name, contact, building address, description and purpose, building drawings. Reviewed within 30 days. Officer inspects after 7 days notice. Certificate issued for one year. Displayed in conspicuous place. Renewal application one month before expiry. Certificate invalid if any violation found."""

TOPIC_HINTS = {
    "fire_basics": "Focus on fire triangle, fire tetrahedron, fire classes (A/B/C/D/F) and their extinguishing agents, flash point, fire point, autoignition, backdraft, flashover, solid and liquid fuel fire behavior from the Firefighting Course.",
    "ppe": "Focus on types of PPE (basic and advanced), protection for each body part (head/hands/feet/breathing/eyes/ears), SCBA components and duration, maintenance and inspection of PPE from both Rescue and Firefighting materials.",
    "fire_suppression": "Focus on fire hose types and sizes, fire pump operations, foam types and expansion rates, extinguisher classes and operating distances, water supply pressures, hydrant types from the Firefighting Course.",
    "fire_vehicles": "Focus on fire ladder types, SCBA specifications (pressure/duration/donning time/DSU), Fire-TEA equipment, building protection systems (sprinkler types, detector types, activation temperatures), repair and maintenance from Firefighting Course.",
    "building_safety": "Focus on Punjab Community Safety Buildings Regulations 2022: exit staircase requirements (travel distance, dimensions, fire rating), exit signs, hydrant specifications (pressure, tank sizes, distances), sprinkler, fire alarm, fire extinguisher placement rules (sizes, travel distances, mounting heights), first aid box contents, AED, HVAC, safety manager functions, certificate procedures.",
    "ropes_knots": "Focus on rope parts (working end, running end, standing part, kern, mantle), utility vs life safety rope differences, static vs dynamic rope characteristics and uses, care before/during/after use, visual and feel inspection, all knot types and their specific uses from Basic Rescue Course.",
    "rope_rescue": "Focus on five rope rescue techniques (rappelling, ascending, lowering, hauling, belay), equipment required (carabiner types, ascender, descender, prussic loops), safety measures and buddy system requirements from Basic Rescue Course.",
    "vehicle_extrication": "Focus on scene safety steps, vehicle stabilization methods, hydraulic rescue tools (spreader/cutter/ram), glass management, spinal precautions, patient assessment sequence from Basic Rescue Course.",
    "ics": "Focus on ICS structure (incident commander, command staff, four general staff sections), span of control (3-7, optimal 5), emergency response levels (1-4), unified command, NIMS principles from Firefighting Course ICS lesson.",
    "disaster_response": "Focus on START triage system (colors and criteria), mass casualty incident management, ICS in disaster context, flood/earthquake response, USAR operations from Basic Rescue Course disaster materials.",
    "first_aid_rescue": "Focus on patient assessment sequence, triage principles, first aid equipment, MFR skills integration with rescue operations from Basic Rescue Course.",
    "fire_risk": "Focus on five steps of fire risk assessment, risk matrix (likelihood x severity), hazard identification categories, fire inspection procedures, building fire safety checklist from Firefighting Course.",
}

SOURCE_CONTENT_MAP = {
    "fire_basics": FIRE_CONTENT,
    "ppe": RESCUE_CONTENT + "\n\n" + FIRE_CONTENT,
    "fire_suppression": FIRE_CONTENT,
    "fire_vehicles": FIRE_CONTENT,
    "building_safety": BUILDING_CONTENT,
    "ropes_knots": RESCUE_CONTENT,
    "rope_rescue": RESCUE_CONTENT,
    "vehicle_extrication": RESCUE_CONTENT,
    "ics": FIRE_CONTENT,
    "disaster_response": RESCUE_CONTENT,
    "first_aid_rescue": RESCUE_CONTENT,
    "fire_risk": FIRE_CONTENT,
}


async def generate_questions(topic_id: str, topic_label: str, designation: str) -> list:
    questions = [
        {
            "q": f"Which of the following best describes safe Rescue 1122 practice for {topic_label} scenario number {i + 1}?",
            "question": f"Which of the following best describes safe Rescue 1122 practice for {topic_label} scenario number {i + 1}?",
            "opts": ["Use approved safe practice", "Ignore scene hazards", "Work without supervision", "Delay reporting risks"],
            "options": ["Use approved safe practice", "Ignore scene hazards", "Work without supervision", "Delay reporting risks"],
            "ans": 0,
            "topic": "Database Question Bank",
        }
        for i in range(25)
    ]
    return [question for question in questions if is_valid_question(question)]


async def generate_feedback(
    staff_name: str,
    designation: str,
    district: str,
    topic_label: str,
    correct: int,
    total: int,
    score_pct: float,
    passed: bool,
    weak_topics: list
) -> str:
    status = "passed" if passed else "did not pass"
    weak_topic_text = ", ".join(weak_topics) if weak_topics else "no weak sub-topics identified"
    next_step = (
        f"Review these weak areas from the official Rescue 1122 training material: {weak_topic_text}."
        if weak_topics
        else "Maintain this standard through regular revision of the official Rescue 1122 training material."
    )
    return (
        f"{staff_name} ({designation}, {district}) scored {correct}/{total} "
        f"({score_pct:.0f}%) in {topic_label} and {status} the evaluation.\n\n"
        f"{next_step}\n\n"
        "Continue practicing with the question bank and focus on accuracy, response discipline, "
        "and applying the training material in operational situations."
    )
