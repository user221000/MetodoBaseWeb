"""Actual PDFs and option transport preserve calculation meaning."""
import pypdf
import pytest

from api.dependencies import build_cliente_from_dict
from api.pdf_generator import PDFGenerator
from core.exportador_opciones import GeneradorPDFConOpciones
from web.services.plan_generation import serialize_macro_options, serialize_option_energy, serialize_option_meal


def client(reported):
    values={'nombre':'Synthetic calculation','edad':30,'peso_kg':68,'estatura_cm':170,
            'nivel_actividad':'moderada','objetivo':'deficit','sexo':'F'}
    if reported:values['grasa_corporal_pct']=20
    return build_cliente_from_dict(values)


def pdf_text(path):
    return ' '.join(page.extract_text() or '' for page in pypdf.PdfReader(str(path)).pages)


@pytest.mark.parametrize('reported',[False,True])
@pytest.mark.parametrize('mode',['fixed','options'])
def test_actual_pdf_marks_assumed_fat_and_never_says_all_weights_are_raw(tmp_path,reported,mode):
    actor=client(reported)
    meal={'kcal_objetivo':500,'kcal_real':500,'alimentos':{'pechuga_de_pollo':100,'arroz_blanco':200}}
    path=tmp_path/(mode+'.pdf')
    if mode=='fixed':
        generator=PDFGenerator()
        data=generator.datos_from_cliente(actor,{'desayuno':meal})
        generator.generar_plan(data,path)
    else:
        macros={'proteina':31,'carbs':0,'grasa':3.6,'kcal':165}
        option={'alimento':'pechuga_de_pollo','gramos':100,'macros':macros,'equivalencia':''}
        plan={'metadata':{'tipo_plan':'opciones'},'desayuno':{
            'kcal_objetivo':500,'energia_min':480,'energia_max':520,
            **{group:{'cantidad_objetivo':30,'opciones':[option]} for group in ('proteinas','carbohidratos','grasas')},
            'vegetales':[]}}
        result=GeneradorPDFConOpciones(str(path)).generar(actor,plan)
        assert result is not None
    text=pdf_text(path)
    assert ('no es una medición' in text) is (not reported)
    assert 'Pesa los alimentos en CRUDO antes de cocinar' not in text
    assert 'Pesa los alimentos en crudo (antes de cocinar)' not in text
    assert 'estado indicado' in text


def test_transport_keeps_group_contribution_distinct_from_whole_meal_target():
    serialized=serialize_macro_options({'cantidad_objetivo':35,'aporte_referencia':20,
        'num_opciones':3,'opciones':[{'alimento':'food','gramos':80,'macros':{'proteina':20}}]})
    assert serialized['cantidad_objetivo']==35 and serialized['aporte_referencia']==20
    assert serialized['num_opciones']==1 and serialized['opciones'][0]['gramos']==80


def test_transport_keeps_real_base_and_range_separate_from_target():
    meal={'kcal_objetivo':500,'kcal_real':497.25,'energia_min':480.5,'energia_max':519.9,
          'desviacion_pct':.55,'macros_reales':{'proteina':30,'carbs':50,'grasa':20,'kcal':497.25},
          'base_selection':{'proteinas':0,'carbohidratos':0,'grasas':0}}
    result=serialize_option_energy(meal)
    assert result['kcal_real']==497.25 and result['energia_min']==480.5 and result['energia_max']==519.9
    assert result['base_selection']==meal['base_selection'] and 'kcal_objetivo' not in result


def test_persisted_target_does_not_round_a_valid_boundary_past_five_percent():
    meal={'kcal_objetivo':543.244,'kcal_real':540.25,'energia_min':524.08,'energia_max':570.30}
    stored=serialize_option_meal(meal)
    assert stored['kcal_objetivo']==543.244
    assert stored['energia_max']<=stored['kcal_objetivo']*1.05
    assert stored['energia_max']>round(stored['kcal_objetivo'])*1.05
