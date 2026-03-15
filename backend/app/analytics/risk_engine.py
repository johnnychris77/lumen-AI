def calculate_risk(issue, confidence):

    risk = 0

    if issue in ["debris", "stain"]:
        risk += 50

    if issue == "corrosion":
        risk += 80

    if confidence > 0.8:
        risk += 20

    if confidence > 0.9:
        risk += 30

    return min(risk,100)
