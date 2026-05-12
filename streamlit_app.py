import streamlit as st
from datetime import date, datetime


# ---------- helpers ----------

def calcular_tfg_ckd_epi_2021(creatinina: float, idade: int, feminino: bool) -> float:
    if feminino:
        kappa, alpha = 0.7, -0.241
    else:
        kappa, alpha = 0.9, -0.302
    razao = creatinina / kappa
    tfg = (
        142
        * (min(razao, 1.0) ** alpha)
        * (max(razao, 1.0) ** -1.200)
        * (0.9938 ** idade)
    )
    if feminino:
        tfg *= 1.012
    return tfg


def init_state():
    if "respostas" not in st.session_state:
        st.session_state.respostas = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }
        st.session_state.step = "dados_basicos"
        st.session_state.mensagens_finais = []
        st.session_state.conduta_final = None


def goto(novo_step: str):
    st.session_state.step = novo_step
    st.rerun()


def encerrar(conduta: str, mensagens):
    st.session_state.conduta_final = conduta
    st.session_state.respostas["conduta_final"] = conduta
    if isinstance(mensagens, str):
        st.session_state.mensagens_finais = [mensagens]
    else:
        st.session_state.mensagens_finais = list(mensagens)
    st.session_state.step = "fim"
    st.rerun()


def reiniciar():
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.rerun()


# ---------- página ----------

st.set_page_config(
    page_title="TC — Auxílio Decisório",
    page_icon="🩺",
    layout="centered",
)

init_state()
R = st.session_state.respostas
step = st.session_state.step

st.title("TC - apoio e orientações a prescrição de contraste iodado")

with st.sidebar:
    st.header("Resumo")
    if R.get("id_solicitacao") is not None:
        st.write(f"**ID solicitação:** {R['id_solicitacao']}")
    if R.get("peso_kg"):
        st.write(f"**Peso:** {R['peso_kg']} kg")
    if R.get("idade_anos") is not None:
        st.write(f"**Idade:** {R['idade_anos']} anos")
    if R.get("sexo_feminino") is not None:
        st.write(f"**Sexo:** {'Feminino' if R['sexo_feminino'] else 'Masculino'}")
    if R.get("tfg") is not None:
        st.write(f"**TFG:** {R['tfg']:.1f} mL/min/1,73 m²")
    st.divider()
    if st.button("🔄 Reiniciar"):
        reiniciar()


# ---------- passos da árvore ----------

if step == "dados_basicos":
    st.subheader("Dados do paciente")
    with st.form("f_dados"):
        id_sol_str = st.text_input("ID da solicitação de TC", value="")
        peso_str = st.text_input("Peso do paciente (kg)", value="")
        idade_str = st.text_input("Idade do paciente (anos)", value="")
        sexo = st.radio(
            "Trata-se de paciente do sexo feminino?",
            ["Não", "Sim"], horizontal=True,
        )
        if st.form_submit_button("Prosseguir", type="primary"):
            try:
                id_sol = int(id_sol_str.strip())
                peso = float(peso_str.replace(",", ".").strip())
                idade = int(idade_str.strip())
            except ValueError:
                st.error("Preencha ID, peso e idade com valores numéricos válidos.")
                st.stop()
            if peso <= 0 or peso > 400:
                st.error("Peso deve estar entre 0,1 e 400 kg.")
                st.stop()
            if idade < 0 or idade > 120:
                st.error("Idade deve estar entre 0 e 120 anos.")
                st.stop()
            R["id_solicitacao"] = id_sol
            R["peso_kg"] = peso
            R["idade_anos"] = idade
            R["sexo_feminino"] = sexo == "Sim"
            goto("gravidez" if R["sexo_feminino"] else "contraste")

elif step == "gravidez":
    st.subheader("Gestação")
    grav = st.radio("A paciente está grávida?", ["Não", "Sim"], horizontal=True, key="r_grav")
    dum = None
    if grav == "Sim":
        dum = st.date_input(
            "Data da última menstruação (DUM)",
            value=None, max_value=date.today(), format="DD/MM/YYYY", key="d_dum",
        )
    if st.button("Prosseguir", type="primary"):
        if grav == "Sim":
            if not dum:
                st.error("Por favor informe a DUM.")
                st.stop()
            R["gravida"] = True
            dias = (date.today() - dum).days
            semanas = dias / 7
            R["idade_gestacional_semanas"] = round(semanas, 1)
            if semanas < 14:
                encerrar(
                    "Contra-indicado (gestação < 14 semanas)",
                    [
                        f"**Idade gestacional estimada:** {semanas:.1f} semanas",
                        "**Exame CONTRA-INDICADO!** Opte por US ou RNM",
                    ],
                )
            else:
                encerrar(
                    "Evitar TC (gestação ≥ 14 semanas)",
                    [
                        f"**Idade gestacional estimada:** {semanas:.1f} semanas",
                        "**Evite TC!** Opte por US ou RNM. Caso seja imprescindível a "
                        "sua realização, realize SEM CONTRASTE, com PROTEÇÃO ADEQUADA "
                        "PARA A PACIENTE, e TERMO DE RESPONSABILIDADE ASSINADO PELO "
                        "MÉDICO ASSISTENTE SOLICITANTE DO EXAME.",
                    ],
                )
        else:
            R["gravida"] = False
            goto("contraste")

elif step == "contraste":
    st.subheader("Contraste iodado")
    with st.form("f_contraste"):
        cont = st.radio(
            "Será necessária administração de CONTRASTE IODADO neste exame?",
            ["Não", "Sim"], horizontal=True,
        )
        if st.form_submit_button("Prosseguir", type="primary"):
            R["contraste_iodado"] = cont == "Sim"
            if not R["contraste_iodado"]:
                encerrar(
                    "TC sem contraste",
                    "Prossiga com a solicitação de Tomografia Computadorizada **SEM** contraste",
                )
            else:
                goto("carater")

elif step == "carater":
    st.subheader("Caráter do exame")
    with st.form("f_carater"):
        car = st.radio(
            "Trata-se de exame de Rotina/Eletivo ou Urgência?",
            ["Rotina/Eletivo", "Urgência"], horizontal=True,
        )
        if st.form_submit_button("Prosseguir", type="primary"):
            R["carater"] = "rotina" if car == "Rotina/Eletivo" else "urgencia"
            goto("jejum" if R["carater"] == "rotina" else "alergia_contraste")

elif step == "jejum":
    st.subheader("Jejum")
    with st.form("f_jejum"):
        j = st.radio(
            "Paciente está em JEJUM HÁ PELO MENOS 4 HORAS?",
            ["Sim", "Não"], horizontal=True,
        )
        if st.form_submit_button("Prosseguir", type="primary"):
            R["jejum_4h"] = j == "Sim"
            if not R["jejum_4h"]:
                encerrar(
                    "Contra-indicado (jejum insuficiente)",
                    "Exame **CONTRA-INDICADO** neste momento. Aguarde 4h de jejum e "
                    "retorne a este fluxograma",
                )
            else:
                goto("alergia_contraste")

elif step == "alergia_contraste":
    st.subheader("Alergia a contraste/iodo")
    with st.form("f_ac"):
        a = st.radio(
            "Paciente com história de ALERGIA a CONTRASTE ou ALERGIA a IODO?",
            ["Não", "Sim"], horizontal=True,
        )
        if st.form_submit_button("Prosseguir", type="primary"):
            R["alergia_contraste_iodo"] = a == "Sim"
            if R["alergia_contraste_iodo"]:
                encerrar(
                    "Contra-indicado (alergia a contraste/iodo)",
                    "Exame **CONTRA-INDICADO!** Opte por TC sem contraste, US ou RNM",
                )
            else:
                goto("hipertireoidismo")

elif step == "hipertireoidismo":
    st.subheader("Hipertireoidismo")
    with st.form("f_ht"):
        h = st.radio("Hipertireoidismo em atividade?", ["Não", "Sim"], horizontal=True)
        if st.form_submit_button("Prosseguir", type="primary"):
            R["hipertireoidismo_ativo"] = h == "Sim"
            if R["hipertireoidismo_ativo"]:
                encerrar(
                    "Contra-indicado (hipertireoidismo em atividade)",
                    "Exame **CONTRA-INDICADO!** Opte por TC sem contraste, US ou RNM",
                )
            else:
                goto("historico_alergia")

elif step == "historico_alergia":
    st.subheader("Histórico alérgico")
    with st.form("f_ha"):
        h = st.radio(
            "Paciente com histórico de Asma, Alergia a medicamentos ou outras substâncias?",
            ["Não", "Sim"], horizontal=True,
        )
        if st.form_submit_button("Prosseguir", type="primary"):
            R["alergia_historico"] = h == "Sim"
            goto("quimio")

elif step == "quimio":
    st.subheader("Quimioterapia")
    quimio = st.radio(
        "Paciente em tratamento oncológico, EM USO ATUAL DE QUIMIOTERAPIA?",
        ["Não", "Sim"], horizontal=True, key="r_quimio",
    )
    data_qt = None
    if quimio == "Sim":
        data_qt = st.date_input(
            "Data do término (ou previsão) de infusão de QT (ou última dose VO)",
            value=None, format="DD/MM/YYYY", key="d_qt",
        )
    if st.button("Prosseguir", type="primary"):
        R["quimioterapia_atual"] = quimio == "Sim"
        if R["quimioterapia_atual"]:
            if not data_qt:
                st.error("Por favor informe a data da QT.")
                st.stop()
            hoje = date.today()
            dias_diff = (data_qt - hoje).days
            R["qt_data"] = data_qt.isoformat()
            R["qt_dias_ate_hoje"] = dias_diff
            if abs(dias_diff) <= 2:
                encerrar(
                    "Contra-indicado (intervalo ≤ 48h em relação à QT)",
                    "Exame **CONTRA-INDICADO** neste momento. Aguarde intervalo de 48h "
                    "antes ou após Quimioterapia para realização do exame. Se "
                    "urgência/emergência, opte por TC sem contraste, US ou RNM",
                )
            else:
                goto("hemodialise")
        else:
            goto("hemodialise")

elif step == "hemodialise":
    st.subheader("Hemodiálise")
    hd = st.radio("Paciente em HEMODIÁLISE?", ["Não", "Sim"], horizontal=True, key="r_hd")
    nefro = None
    if hd == "Sim":
        nefro = st.radio(
            "Caso discutido e acordado com Nefrologia?",
            ["Não", "Sim"], horizontal=True, key="r_nefro",
        )
    if st.button("Prosseguir", type="primary"):
        R["hemodialise"] = hd == "Sim"
        R["pular_para_creatinina"] = False
        if R["hemodialise"]:
            R["nefro_acordado"] = nefro == "Sim"
            if not R["nefro_acordado"]:
                encerrar(
                    "Contra-indicado (hemodiálise sem acordo da Nefrologia)",
                    "Exame **CONTRA-INDICADO!** Discuta o caso com a equipe de "
                    "Nefrologia e retorne posteriormente a este fluxograma. Se "
                    "urgência/emergência, opte por TC sem contraste, US ou RNM",
                )
            else:
                R["pular_para_creatinina"] = True
                goto("creatinina")
        else:
            goto("dm2")

elif step == "dm2":
    st.subheader("Diabetes")
    with st.form("f_dm2"):
        d = st.radio(
            "Paciente portador de Diabetes Mellitus tipo 2?",
            ["Não", "Sim"], horizontal=True,
        )
        if st.form_submit_button("Prosseguir", type="primary"):
            R["dm2"] = d == "Sim"
            R["metformina"] = False
            if R["dm2"]:
                goto("metformina")
            else:
                goto("has")

elif step == "metformina":
    st.subheader("Metformina")
    with st.form("f_metf"):
        m = st.radio("Faz uso de Metformina (VO)?", ["Não", "Sim"], horizontal=True)
        if st.form_submit_button("Prosseguir", type="primary"):
            R["metformina"] = m == "Sim"
            if R["idade_anos"] > 60:
                R["pular_para_creatinina"] = True
                goto("creatinina")
            else:
                goto("has")

elif step == "has":
    st.subheader("Hipertensão arterial sistêmica")
    with st.form("f_has"):
        h = st.radio(
            "Paciente portador de Hipertensão Arterial Sistêmica?",
            ["Não", "Sim"], horizontal=True,
        )
        if st.form_submit_button("Prosseguir", type="primary"):
            R["has"] = h == "Sim"
            if R["has"] and R["idade_anos"] > 60:
                R["pular_para_creatinina"] = True
                goto("creatinina")
            else:
                goto("rim_unico")

elif step == "rim_unico":
    st.subheader("Anomalia renal")
    with st.form("f_rim"):
        r = st.radio(
            "Paciente portador de Rim único ou Rim em ferradura?",
            ["Não", "Sim"], horizontal=True,
        )
        if st.form_submit_button("Prosseguir", type="primary"):
            R["rim_unico_ferradura"] = r == "Sim"
            if R["rim_unico_ferradura"]:
                R["pular_para_creatinina"] = True
                goto("creatinina")
            else:
                goto("tipo_exame")

elif step == "creatinina":
    st.subheader("Creatinina sérica")
    with st.form("f_creat"):
        data_creat = st.date_input(
            "Data da dosagem mais recente de creatinina",
            value=None, max_value=date.today(), format="DD/MM/YYYY",
        )
        creat_val = st.number_input(
            "Resultado da creatinina (mg/dL)",
            min_value=0.01, max_value=30.0, step=0.01, value=1.00, format="%.2f",
        )
        if st.form_submit_button("Prosseguir", type="primary"):
            if not data_creat:
                st.error("Por favor informe a data do exame.")
                st.stop()
            R["creatinina_data"] = data_creat.isoformat()
            R["creatinina_mg_dl"] = float(creat_val)
            tfg = calcular_tfg_ckd_epi_2021(
                creatinina=float(creat_val),
                idade=R["idade_anos"],
                feminino=R["sexo_feminino"],
            )
            R["tfg"] = round(tfg, 1)
            R["cuidados_pos_contraste"] = False

            if tfg < 30:
                encerrar(
                    "Contra-indicado (TFG < 30)",
                    [
                        f"**TFG calculada:** {tfg:.1f} mL/min/1,73 m²",
                        "Exame **CONTRA-INDICADO!** Se urgência/emergência, opte por "
                        "TC sem contraste, US ou RNM",
                    ],
                )
            elif 30 <= tfg < 45:
                goto("q12c")
            elif 45 <= tfg < 60:
                goto("q12b")
            else:
                goto("tipo_exame")

elif step == "q12b":
    st.subheader("Avaliação clínica — TFG 45–59")
    st.info(f"TFG calculada: **{R['tfg']:.1f}** mL/min/1,73 m²")
    with st.form("f_q12b"):
        b = st.radio("Os benefícios são maiores que os riscos?", ["Não", "Sim"], horizontal=True)
        if st.form_submit_button("Prosseguir", type="primary"):
            R["q12b_beneficios_maiores"] = b == "Sim"
            if not R["q12b_beneficios_maiores"]:
                encerrar(
                    "Contra-indicado (TFG 45–59, sem benefício superior ao risco)",
                    "Exame **CONTRA-INDICADO!** Se urgência/emergência, opte por TC "
                    "sem contraste, US ou RNM",
                )
            else:
                R["cuidados_pos_contraste"] = True
                goto("tipo_exame")

elif step == "q12c":
    st.subheader("Avaliação clínica — TFG 30–44")
    st.warning(f"TFG calculada: **{R['tfg']:.1f}** mL/min/1,73 m²")
    with st.form("f_q12c"):
        i = st.radio(
            "Este exame é IMPRESCÍNDIVEL para o diagnóstico/condução do caso?",
            ["Não", "Sim"], horizontal=True,
        )
        if st.form_submit_button("Prosseguir", type="primary"):
            R["q12c_imprescindivel"] = i == "Sim"
            if not R["q12c_imprescindivel"]:
                encerrar(
                    "Contra-indicado (TFG 30–44, exame não imprescindível)",
                    "Exame **CONTRA-INDICADO!** Se urgência/emergência, opte por TC "
                    "sem contraste, US ou RNM",
                )
            else:
                R["cuidados_pos_contraste"] = True
                goto("tipo_exame")

elif step == "tipo_exame":
    st.subheader("Tipo de exame contrastado")
    with st.form("f_tipo"):
        opcoes = {
            "1": "TC Simples (não-abdome) / AngioTC / Arterial",
            "2": "TC Abdome / Fase Venosa / TC com Duplo contraste",
            "3": "TC com Triplo contraste (três fases)",
        }
        rotulos = [f"{k} — {v}" for k, v in opcoes.items()]
        escolha = st.radio("Escolha o tipo de exame:", rotulos)
        if st.form_submit_button("Concluir", type="primary"):
            tipo = escolha.split(" — ")[0]
            multiplicadores = {"1": 1.0, "2": 1.2, "3": 1.5}
            tetos = {"1": 100, "2": 130, "3": 150}
            peso = R["peso_kg"]
            volume = min(peso * multiplicadores[tipo], tetos[tipo])
            R["tipo_exame"] = tipo
            R["volume_contraste_ml"] = round(volume, 1)

            mensagens = [
                f"Você deverá prescrever **{volume:.0f} mL** de contraste iodado para "
                "este paciente"
            ]

            if R.get("alergia_historico"):
                mensagens.append(
                    "⚠️ **ATENÇÃO!** Prescreva também OBRIGATORIAMENTE o preparo "
                    "anti-alérgico: **Hidrocortisona 200mg EV** 1 hora antes do exame "
                    "+ **Difenidramina 50mg EV** 1 hora antes do exame"
                )

            if R.get("metformina") and R.get("tfg") is not None and 30 <= R["tfg"] < 45:
                mensagens.append(
                    "⚠️ **ATENÇÃO!** **METFORMINA**: suspenda no dia do exame e mantenha "
                    "suspensa até 48h após o procedimento. Reintroduza somente se não "
                    "houver alteração da função renal."
                )

            if R.get("cuidados_pos_contraste"):
                sf_antes = R["peso_kg"] * 3
                sf_depois = R["peso_kg"] * 4
                mensagens.append(
                    "⚠️ **ATENÇÃO!** Prescreva os cuidados pós-contraste iodado após a "
                    "realização do exame, e entre em contato com a equipe de Nefrologia "
                    "para discussão do caso."
                )
                mensagens.append(
                    f"Você deverá prescrever **SF 0,9% {sf_antes:.0f} mL** para infusão "
                    "EM QUATRO HORAS ANTES DO EXAME"
                )
                mensagens.append(
                    f"Você deverá prescrever **SF 0,9% {sf_depois:.0f} mL** para infusão "
                    "EM QUATRO HORAS DEPOIS DO EXAME"
                )

            encerrar(f"TC com contraste — {volume:.0f} mL", mensagens)

elif step == "fim":
    st.subheader("Resultado")
    conduta = st.session_state.conduta_final or ""
    if "Contra-indicado" in conduta:
        st.error(f"**Conduta:** {conduta}")
    elif "Evitar" in conduta:
        st.warning(f"**Conduta:** {conduta}")
    else:
        st.success(f"**Conduta:** {conduta}")

    for msg in st.session_state.mensagens_finais:
        st.markdown(msg)

    st.divider()
    st.write(
        "Obrigado por suas respostas. Se dúvidas, entre em contato com a Diretoria "
        "Médica. Até breve!"
    )
    if st.button("Nova Consulta", type="primary"):
        reiniciar()


# ---------- créditos (rodapé global) ----------

st.divider()
st.caption(
    "**Elaboração do Fluxograma:** Dra Erika Ortolan e Dra Giovana Comes  \n"
    "**Desenvolvimento e Script em Python:** Dr Wilson Oliveira Jr"
)
