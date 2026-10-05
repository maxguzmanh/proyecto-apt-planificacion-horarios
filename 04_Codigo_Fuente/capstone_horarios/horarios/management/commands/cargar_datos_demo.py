from datetime import date, time

from django.core.management.base import BaseCommand
from django.db import transaction

from academico.models import (
    AreaAcademica,
    Asignatura,
    Aula,
    CentroTutorial,
    Facultad,
    Modalidad,
    PeriodoAcademico,
    PlanEstudioAsignatura,
    Profesor,
    ProgramaAcademico,
    ProgramaCentroTutorial,
    Sede,
    Semestre,
)

from horarios.models import (
    Grupo,
    Horario,
    OfertaAcademica,
    OfertaGrupo,
)


class Command(BaseCommand):

    help = "Carga datos ficticios para probar el sistema " "de planificación docente."

    @transaction.atomic
    def handle(self, *args, **options):

        self.stdout.write(self.style.WARNING("Iniciando carga de datos ficticios..."))

        # ==================================================
        # CENTRO TUTORIAL
        # ==================================================

        centro, _ = CentroTutorial.objects.update_or_create(
            codigo="CT-DEMO",
            defaults={
                "nombre": "Centro Tutorial Ciudad Demo",
                "activo": True,
            },
        )

        # ==================================================
        # SEDES
        # ==================================================

        sede_academica, _ = Sede.objects.update_or_create(
            centro_tutorial=centro,
            codigo="SEDE-ACA",
            defaults={
                "nombre": "Sede Académica",
                "activo": True,
            },
        )

        sede_norte, _ = Sede.objects.update_or_create(
            centro_tutorial=centro,
            codigo="SEDE-NORTE",
            defaults={
                "nombre": "Sede Norte",
                "activo": True,
            },
        )

        sede_virtual, _ = Sede.objects.update_or_create(
            centro_tutorial=centro,
            codigo="SEDE-VIR",
            defaults={
                "nombre": "Campus Virtual",
                "activo": True,
            },
        )

        # ==================================================
        # FACULTADES
        # ==================================================

        facultad_ingenieria, _ = Facultad.objects.update_or_create(
            codigo="FING",
            defaults={
                "nombre": "Facultad de Ingeniería y Tecnología",
                "activo": True,
            },
        )

        facultad_administrativa, _ = Facultad.objects.update_or_create(
            codigo="FADM",
            defaults={
                "nombre": "Facultad de Ciencias Administrativas",
                "activo": True,
            },
        )

        # ==================================================
        # PROGRAMAS ACADÉMICOS
        # ==================================================

        informatica, _ = ProgramaAcademico.objects.update_or_create(
            codigo="ING-INF",
            defaults={
                "nombre": "Ingeniería Informática",
                "facultad": facultad_ingenieria,
                "activo": True,
            },
        )

        industrial, _ = ProgramaAcademico.objects.update_or_create(
            codigo="ING-IND",
            defaults={
                "nombre": "Ingeniería Industrial",
                "facultad": facultad_ingenieria,
                "activo": True,
            },
        )

        tecnologia, _ = ProgramaAcademico.objects.update_or_create(
            codigo="TEC-SIS",
            defaults={
                "nombre": "Tecnología en Sistemas",
                "facultad": facultad_ingenieria,
                "activo": True,
            },
        )

        administracion, _ = ProgramaAcademico.objects.update_or_create(
            codigo="ADM-EMP",
            defaults={
                "nombre": "Administración de Empresas",
                "facultad": facultad_administrativa,
                "activo": True,
            },
        )

        contaduria, _ = ProgramaAcademico.objects.update_or_create(
            codigo="CONT-PUB",
            defaults={
                "nombre": "Contaduría Pública",
                "facultad": facultad_administrativa,
                "activo": True,
            },
        )

        programas = [
            informatica,
            industrial,
            tecnologia,
            administracion,
            contaduria,
        ]

        # ==================================================
        # PROGRAMAS DISPONIBLES EN EL CENTRO TUTORIAL
        # ==================================================

        for programa in programas:

            ProgramaCentroTutorial.objects.update_or_create(
                programa=programa,
                centro_tutorial=centro,
                defaults={
                    "activo": True,
                },
            )

        # ==================================================
        # PERIODO ACADÉMICO
        # ==================================================

        periodo, _ = PeriodoAcademico.objects.update_or_create(
            codigo="01-2026",
            defaults={
                "nombre": "01-2026",
                "fecha_inicio": date(2026, 1, 19),
                "fecha_fin": date(2026, 6, 30),
                "activo": True,
            },
        )

        # ==================================================
        # SEMESTRES
        # ==================================================

        semestres = {}

        for numero in range(1, 11):

            semestre, _ = Semestre.objects.get_or_create(
                numero=numero,
            )

            semestres[numero] = semestre

        # ==================================================
        # MODALIDADES
        # ==================================================

        presencial, _ = Modalidad.objects.update_or_create(
            codigo="PRE",
            defaults={
                "nombre": "Presencial",
                "activo": True,
            },
        )

        virtual, _ = Modalidad.objects.update_or_create(
            codigo="VIR",
            defaults={
                "nombre": "Virtual",
                "activo": True,
            },
        )

        hibrida, _ = Modalidad.objects.update_or_create(
            codigo="HIB",
            defaults={
                "nombre": "Híbrida",
                "activo": True,
            },
        )

        # ==================================================
        # ÁREAS ACADÉMICAS
        # ==================================================

        area_informatica, _ = AreaAcademica.objects.update_or_create(
            codigo="INF",
            defaults={
                "nombre": "Informática",
                "activo": True,
            },
        )

        area_numerica, _ = AreaAcademica.objects.update_or_create(
            codigo="NUM",
            defaults={
                "nombre": "Área Numérica",
                "activo": True,
            },
        )

        area_humanidades, _ = AreaAcademica.objects.update_or_create(
            codigo="HUM",
            defaults={
                "nombre": "Humanidades",
                "activo": True,
            },
        )

        area_investigacion, _ = AreaAcademica.objects.update_or_create(
            codigo="INV",
            defaults={
                "nombre": "Investigación",
                "activo": True,
            },
        )

        area_administrativa, _ = AreaAcademica.objects.update_or_create(
            codigo="ADM",
            defaults={
                "nombre": "Administración y Gestión",
                "activo": True,
            },
        )

        # ==================================================
        # ASIGNATURAS
        # ==================================================

        datos_asignaturas = [
            ("PROGWEB01", "Programación Web"),
            ("BD01", "Bases de Datos"),
            ("SO01", "Sistemas Operativos"),
            ("ARQ01", "Arquitectura de Software"),
            ("COMP001", "Competencias Comunicativas"),
            ("DIGI001", "Competencias Digitales"),
            ("LOG001", "Pensamiento Lógico Matemático"),
            ("EST001", "Estadística Descriptiva"),
            ("GEST001", "Gestión de Proyectos"),
            ("CONT001", "Fundamentos de Contabilidad"),
            ("INV001", "Metodología de la Investigación"),
        ]

        asignaturas = {}

        for codigo, nombre in datos_asignaturas:

            asignatura, _ = Asignatura.objects.update_or_create(
                codigo=codigo,
                defaults={
                    "nombre": nombre,
                    "activo": True,
                },
            )

            asignaturas[codigo] = asignatura

        # ==================================================
        # PLANES DE ESTUDIO
        # ==================================================

        def crear_plan(
            programa,
            codigo_asignatura,
            semestre,
            creditos,
            area,
        ):

            PlanEstudioAsignatura.objects.update_or_create(
                programa=programa,
                asignatura=asignaturas[codigo_asignatura],
                semestre=semestres[semestre],
                defaults={
                    "creditos": creditos,
                    "area_academica": area,
                    "activo": True,
                },
            )

        # --------------------------------------------------
        # Ingeniería Informática
        # --------------------------------------------------

        crear_plan(
            informatica,
            "COMP001",
            1,
            2,
            area_humanidades,
        )

        crear_plan(
            informatica,
            "DIGI001",
            1,
            2,
            area_informatica,
        )

        crear_plan(
            informatica,
            "LOG001",
            1,
            3,
            area_numerica,
        )

        crear_plan(
            informatica,
            "EST001",
            1,
            3,
            area_numerica,
        )

        crear_plan(
            informatica,
            "PROGWEB01",
            5,
            3,
            area_informatica,
        )

        crear_plan(
            informatica,
            "BD01",
            5,
            3,
            area_informatica,
        )

        crear_plan(
            informatica,
            "SO01",
            5,
            3,
            area_informatica,
        )

        crear_plan(
            informatica,
            "ARQ01",
            5,
            3,
            area_informatica,
        )

        crear_plan(
            informatica,
            "GEST001",
            6,
            3,
            area_administrativa,
        )

        crear_plan(
            informatica,
            "INV001",
            6,
            2,
            area_investigacion,
        )

        # --------------------------------------------------
        # Ingeniería Industrial
        # --------------------------------------------------

        crear_plan(
            industrial,
            "COMP001",
            1,
            2,
            area_humanidades,
        )

        crear_plan(
            industrial,
            "DIGI001",
            1,
            2,
            area_informatica,
        )

        crear_plan(
            industrial,
            "LOG001",
            1,
            3,
            area_numerica,
        )

        crear_plan(
            industrial,
            "EST001",
            1,
            3,
            area_numerica,
        )

        crear_plan(
            industrial,
            "GEST001",
            5,
            3,
            area_administrativa,
        )

        crear_plan(
            industrial,
            "INV001",
            6,
            2,
            area_investigacion,
        )

        # --------------------------------------------------
        # Tecnología en Sistemas
        #
        # DIGI001 tiene 3 créditos aquí.
        # Esto demuestra que los créditos pertenecen
        # al plan y no directamente a Asignatura.
        # --------------------------------------------------

        crear_plan(
            tecnologia,
            "COMP001",
            1,
            2,
            area_humanidades,
        )

        crear_plan(
            tecnologia,
            "DIGI001",
            1,
            3,
            area_informatica,
        )

        crear_plan(
            tecnologia,
            "LOG001",
            1,
            2,
            area_numerica,
        )

        crear_plan(
            tecnologia,
            "EST001",
            1,
            3,
            area_numerica,
        )

        crear_plan(
            tecnologia,
            "PROGWEB01",
            4,
            3,
            area_informatica,
        )

        # --------------------------------------------------
        # Administración de Empresas
        # --------------------------------------------------

        crear_plan(
            administracion,
            "COMP001",
            1,
            3,
            area_humanidades,
        )

        crear_plan(
            administracion,
            "DIGI001",
            1,
            2,
            area_informatica,
        )

        crear_plan(
            administracion,
            "LOG001",
            1,
            2,
            area_numerica,
        )

        crear_plan(
            administracion,
            "EST001",
            1,
            3,
            area_numerica,
        )

        crear_plan(
            administracion,
            "CONT001",
            1,
            3,
            area_administrativa,
        )

        crear_plan(
            administracion,
            "GEST001",
            4,
            3,
            area_administrativa,
        )

        crear_plan(
            administracion,
            "INV001",
            5,
            2,
            area_investigacion,
        )

        # --------------------------------------------------
        # Contaduría Pública
        # --------------------------------------------------

        crear_plan(
            contaduria,
            "COMP001",
            1,
            2,
            area_humanidades,
        )

        crear_plan(
            contaduria,
            "DIGI001",
            1,
            2,
            area_informatica,
        )

        crear_plan(
            contaduria,
            "LOG001",
            1,
            2,
            area_numerica,
        )

        crear_plan(
            contaduria,
            "EST001",
            1,
            3,
            area_numerica,
        )

        crear_plan(
            contaduria,
            "CONT001",
            1,
            4,
            area_administrativa,
        )

        crear_plan(
            contaduria,
            "INV001",
            4,
            2,
            area_investigacion,
        )

        # ==================================================
        # PROFESORES FICTICIOS
        # ==================================================

        datos_profesores = [
            (
                "DOC-DEMO-001",
                "Laura",
                "Méndez",
                "laura.mendez@demo.edu",
            ),
            (
                "DOC-DEMO-002",
                "Diego",
                "Herrera",
                "diego.herrera@demo.edu",
            ),
            (
                "DOC-DEMO-003",
                "Camila",
                "Rojas",
                "camila.rojas@demo.edu",
            ),
            (
                "DOC-DEMO-004",
                "Sofía",
                "Navarro",
                "sofia.navarro@demo.edu",
            ),
            (
                "DOC-DEMO-005",
                "Andrés",
                "Salazar",
                "andres.salazar@demo.edu",
            ),
            (
                "DOC-DEMO-006",
                "Felipe",
                "Campos",
                "felipe.campos@demo.edu",
            ),
        ]

        profesores = {}

        for (
            identificacion,
            nombre,
            apellido,
            correo,
        ) in datos_profesores:

            profesor, _ = Profesor.objects.update_or_create(
                identificacion=identificacion,
                defaults={
                    "nombre": nombre,
                    "apellido": apellido,
                    "correo_institucional": correo,
                    "activo": True,
                },
            )

            profesores[identificacion] = profesor

        # ==================================================
        # AULAS
        # ==================================================

        aula_101, _ = Aula.objects.update_or_create(
            sede=sede_academica,
            codigo="A-101",
            defaults={
                "nombre": "Sala 101",
                "capacidad": 35,
                "tipo": Aula.TIPO_FISICA,
                "activo": True,
            },
        )

        aula_201, _ = Aula.objects.update_or_create(
            sede=sede_academica,
            codigo="A-201",
            defaults={
                "nombre": "Sala 201",
                "capacidad": 40,
                "tipo": Aula.TIPO_FISICA,
                "activo": True,
            },
        )

        laboratorio, _ = Aula.objects.update_or_create(
            sede=sede_academica,
            codigo="LAB-01",
            defaults={
                "nombre": "Laboratorio de Informática",
                "capacidad": 30,
                "tipo": Aula.TIPO_FISICA,
                "activo": True,
            },
        )

        aula_norte, _ = Aula.objects.update_or_create(
            sede=sede_norte,
            codigo="N-101",
            defaults={
                "nombre": "Sala Norte 101",
                "capacidad": 35,
                "tipo": Aula.TIPO_FISICA,
                "activo": True,
            },
        )

        auditorio, _ = Aula.objects.update_or_create(
            sede=sede_norte,
            codigo="AUD-01",
            defaults={
                "nombre": "Auditorio Principal",
                "capacidad": 100,
                "tipo": Aula.TIPO_FISICA,
                "activo": True,
            },
        )

        aula_virtual, _ = Aula.objects.update_or_create(
            sede=sede_virtual,
            codigo="VIR",
            defaults={
                "nombre": "Aula Virtual",
                "capacidad": 0,
                "tipo": Aula.TIPO_VIRTUAL,
                "activo": True,
            },
        )

        # ==================================================
        # GRUPOS
        # ==================================================

        def crear_grupo(
            codigo,
            programa,
            semestre,
        ):

            grupo, _ = Grupo.objects.update_or_create(
                codigo=codigo,
                programa=programa,
                centro_tutorial=centro,
                periodo=periodo,
                semestre=semestres[semestre],
                defaults={
                    "activo": True,
                },
            )

            return grupo

        info_1_g1 = crear_grupo(
            "01PD G1",
            informatica,
            1,
        )

        info_5_g1 = crear_grupo(
            "05PD G1",
            informatica,
            5,
        )

        info_5_g2 = crear_grupo(
            "05PD G2",
            informatica,
            5,
        )

        industrial_1_g1 = crear_grupo(
            "01PD G1",
            industrial,
            1,
        )

        tecnologia_1_g1 = crear_grupo(
            "01PD G1",
            tecnologia,
            1,
        )

        administracion_1_g1 = crear_grupo(
            "01PD G1",
            administracion,
            1,
        )

        contaduria_1_g1 = crear_grupo(
            "01PD G1",
            contaduria,
            1,
        )

        # ==================================================
        # FUNCIONES AUXILIARES PARA OFERTAS
        # ==================================================

        def crear_oferta(
            codigo_asignatura,
            profesor,
            modalidad,
        ):

            oferta, _ = OfertaAcademica.objects.get_or_create(
                asignatura=asignaturas[codigo_asignatura],
                profesor=profesor,
                periodo=periodo,
                modalidad=modalidad,
                defaults={
                    "activo": True,
                },
            )

            if not oferta.activo:
                oferta.activo = True
                oferta.save()

            return oferta

        def agregar_grupo(
            oferta,
            grupo,
            cupos,
        ):

            oferta_grupo, _ = OfertaGrupo.objects.update_or_create(
                oferta=oferta,
                grupo=grupo,
                defaults={
                    "cupos": cupos,
                },
            )

            oferta_grupo.full_clean()
            oferta_grupo.save()

        def crear_horario(
            oferta,
            aula,
            dia,
            hora_inicio,
            hora_fin,
        ):

            horario, _ = Horario.objects.get_or_create(
                oferta=oferta,
                aula=aula,
                dia=dia,
                hora_inicio=hora_inicio,
                hora_fin=hora_fin,
                defaults={
                    "activo": True,
                },
            )

            horario.activo = True

            horario.full_clean()
            horario.save()

            return horario

        # ==================================================
        # OFERTAS NORMALES
        # ==================================================

        oferta_programacion = crear_oferta(
            "PROGWEB01",
            profesores["DOC-DEMO-001"],
            presencial,
        )

        agregar_grupo(
            oferta_programacion,
            info_5_g1,
            30,
        )

        crear_horario(
            oferta_programacion,
            aula_101,
            "LU",
            time(8, 0),
            time(10, 0),
        )

        # --------------------------------------------------

        oferta_bd = crear_oferta(
            "BD01",
            profesores["DOC-DEMO-002"],
            presencial,
        )

        agregar_grupo(
            oferta_bd,
            info_5_g1,
            30,
        )

        crear_horario(
            oferta_bd,
            aula_201,
            "MI",
            time(10, 0),
            time(12, 0),
        )

        # --------------------------------------------------

        oferta_so = crear_oferta(
            "SO01",
            profesores["DOC-DEMO-003"],
            presencial,
        )

        agregar_grupo(
            oferta_so,
            info_5_g2,
            28,
        )

        crear_horario(
            oferta_so,
            laboratorio,
            "MA",
            time(8, 0),
            time(10, 0),
        )

        # --------------------------------------------------

        oferta_arquitectura = crear_oferta(
            "ARQ01",
            profesores["DOC-DEMO-001"],
            hibrida,
        )

        agregar_grupo(
            oferta_arquitectura,
            info_5_g2,
            28,
        )

        crear_horario(
            oferta_arquitectura,
            aula_101,
            "VI",
            time(14, 0),
            time(16, 0),
        )

        # ==================================================
        # OFERTA TRANSVERSAL:
        # COMPETENCIAS COMUNICATIVAS
        # ==================================================

        oferta_comunicativas = crear_oferta(
            "COMP001",
            profesores["DOC-DEMO-004"],
            presencial,
        )

        agregar_grupo(
            oferta_comunicativas,
            info_1_g1,
            30,
        )

        agregar_grupo(
            oferta_comunicativas,
            industrial_1_g1,
            35,
        )

        agregar_grupo(
            oferta_comunicativas,
            administracion_1_g1,
            32,
        )

        agregar_grupo(
            oferta_comunicativas,
            contaduria_1_g1,
            30,
        )

        crear_horario(
            oferta_comunicativas,
            auditorio,
            "JU",
            time(10, 0),
            time(12, 0),
        )

        # ==================================================
        # OFERTA TRANSVERSAL VIRTUAL:
        # COMPETENCIAS DIGITALES
        # ==================================================

        oferta_digitales = crear_oferta(
            "DIGI001",
            profesores["DOC-DEMO-005"],
            virtual,
        )

        agregar_grupo(
            oferta_digitales,
            info_1_g1,
            30,
        )

        agregar_grupo(
            oferta_digitales,
            industrial_1_g1,
            35,
        )

        agregar_grupo(
            oferta_digitales,
            tecnologia_1_g1,
            30,
        )

        crear_horario(
            oferta_digitales,
            aula_virtual,
            "MA",
            time(18, 0),
            time(20, 0),
        )

        # ==================================================
        # OTRA OFERTA TRANSVERSAL
        # ==================================================

        oferta_logica = crear_oferta(
            "LOG001",
            profesores["DOC-DEMO-006"],
            presencial,
        )

        agregar_grupo(
            oferta_logica,
            administracion_1_g1,
            32,
        )

        agregar_grupo(
            oferta_logica,
            contaduria_1_g1,
            30,
        )

        crear_horario(
            oferta_logica,
            aula_norte,
            "SA",
            time(8, 0),
            time(10, 0),
        )

        # ==================================================
        # CLASE DOMINICAL DE PRUEBA
        # ==================================================

        oferta_contabilidad = crear_oferta(
            "CONT001",
            profesores["DOC-DEMO-003"],
            presencial,
        )

        agregar_grupo(
            oferta_contabilidad,
            contaduria_1_g1,
            30,
        )

        crear_horario(
            oferta_contabilidad,
            aula_201,
            "DO",
            time(9, 0),
            time(11, 0),
        )

        # ==================================================
        # RESUMEN
        # ==================================================

        self.stdout.write("")

        self.stdout.write(self.style.SUCCESS("Datos ficticios cargados correctamente."))

        self.stdout.write(f"Centros Tutoriales: " f"{CentroTutorial.objects.count()}")

        self.stdout.write(f"Sedes: " f"{Sede.objects.count()}")

        self.stdout.write(f"Facultades: " f"{Facultad.objects.count()}")

        self.stdout.write(
            f"Programas Académicos: " f"{ProgramaAcademico.objects.count()}"
        )

        self.stdout.write(f"Asignaturas: " f"{Asignatura.objects.count()}")

        self.stdout.write(f"Profesores: " f"{Profesor.objects.count()}")

        self.stdout.write(f"Aulas: " f"{Aula.objects.count()}")

        self.stdout.write(f"Grupos: " f"{Grupo.objects.count()}")

        self.stdout.write(f"Ofertas Académicas: " f"{OfertaAcademica.objects.count()}")

        self.stdout.write(f"Horarios: " f"{Horario.objects.count()}")
