import cmath
from distutils.command import clean
import math
import os
import time
from typing import List
import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import List
from datetime import datetime
from collections import namedtuple
import cmath
import concurrent.futures as cf
import multiprocessing as mp
import threading
import asyncio

class Barra:
    def __init__(self):
        self.Numero = 0  # A identificação da barra (ID)
        self.S = []  # Criação de um vetor complexo de potência
        self.ramosJusante = []  # Lista de ramos jusante
        self.V = []  # Vetor complexo de tensão
        self.ramoMontante = None  # Ramo montante
        self.I = []  # Vetor complexo da injeção de corrente na barra, corrente consumida pela barra


class Ramo:
    def __init__(self):
        # Dados de entrada
        self.bDe = 0  # Barra de origem (From)
        self.bPara = 0  # Barra de destino (to)
        self.zramo = [[]]  # Declaração da matriz de impedância da linha
        self.barraDe = None  # Variável barra do tipo Barra adicionada no Ramo
        self.barraPara = None
        self.ramoMontante = None  # Variável do tipo Ramo, ramoMontante adicionada no Ramo
        self.J = []  # Vetor complexo corrente J

        # Variáveis de pré-processamento
        self.isMain = False  # Pertence ao caminho principal da rede
        self.accDB = 0  # Quantidade de barras a jusante do ramo
        self.depth = 0  # Profundidade do ramo

        # Variáveis auxiliares do paralelismo
        self.ForkJoin = False  # Permite o paralelismo


class Rede:
    def __init__(self):
        self.barras = []
        self.ramos = []
        self.vSE = 13800
        self.ComT = time.process_time()
        self.GetTime = True
        self.dTbyRun = []
        self.Npontos = 100
        self.ListaAdj = []
        self.fjThreshould = 50
        self.Nucleos = 1
        self.Nucleosdisponiveis = 0

    class Rede:
        def __init__(self):
            self.barras = []
            self.ramos = []
            self.vSE = 13800
            self.ComT = None
            self.GetTime = True
            self.dTbyRun = []
            self.Npontos = 100
            self.ListaAdj = []
            self.fjThreshould = 50
            self.Nucleos = 1
            self.Nucleosdisponiveis = 0

    def lerRede(self, dadoRD):
        ramosxml = dadoRD.find("Branch")
        barrasxml = dadoRD.find("Bus")

        multiS = float(barrasxml.get("multiS"))
        self.barras = [Barra() for _ in range(len(barrasxml))]
        for i, barra in enumerate(barrasxml):
            self.barras[i].Numero = int(barra.get("id"))
            self.barras[i].S = [
                complex(float(barra.get("pa")) * multiS, float(barra.get("qa")) * multiS),
                complex(float(barra.get("pb")) * multiS, float(barra.get("qb")) * multiS),
                complex(float(barra.get("pc")) * multiS, float(barra.get("qc")) * multiS)
            ]

        self.ramos = [Ramo() for _ in range(len(ramosxml))]
        for i, ramo in enumerate(ramosxml):
            self.ramos[i].bDe = int(ramo.get("from"))
            self.ramos[i].bPara = int(ramo.get("to"))
            self.ramos[i].zramo = [
                [
                    complex(float(ramo.get("raa")), float(ramo.get("xaa"))),
                    complex(float(ramo.get("rab")), float(ramo.get("xab"))),
                    complex(float(ramo.get("rac")), float(ramo.get("xac")))
                ],
                [
                    complex(float(ramo.get("rab")), float(ramo.get("xab"))),
                    complex(float(ramo.get("rbb")), float(ramo.get("xbb"))),
                    complex(float(ramo.get("rbc")), float(ramo.get("xbc")))
                ],
                [
                    complex(float(ramo.get("rac")), float(ramo.get("xac"))),
                    complex(float(ramo.get("rbc")), float(ramo.get("xbc"))),
                    complex(float(ramo.get("rcc")), float(ramo.get("xcc")))
                ]
            ]
            barraDe_numero = self.ramos[i].bDe
            barraPara_numero = self.ramos[i].bPara

            self.ramos[i].barraDe = next(barra for barra in self.barras if barra.Numero == barraDe_numero)
            self.ramos[i].barraPara = next(barra for barra in self.barras if barra.Numero == barraPara_numero)

            self.ramos[i].barraDe.ramosJusante.append(self.ramos[i])

        for i in range(len(self.ramos)):
            for j in range(len(self.ramos)):
                if self.ramos[i].bDe == self.ramos[j].bPara:
                    self.ramos[i].ramoMontante = self.ramos[j]
                    break

        # Criação da lista de adjascentes
        def getListaAdj(line):
            self.ListaAdj.append(line)
            for RamoJus in line.barraPara.ramosJusante:
                getListaAdj(RamoJus)

        getListaAdj(self.ramos[0])

        # Determina a profundidade e o ramo mais profundo
        Deepest = Ramo()

        def getDepth(line):
            nonlocal Deepest
            line.depth = line.ramoMontante.depth + 1
            if line.depth > Deepest.depth:
                Deepest = line

            line.accDB = 1
            for i in range(len(line.barraPara.ramosJusante)):
                getDepth(line.barraPara.ramosJusante[i])
                line.accDB += line.barraPara.ramosJusante[i].accDB

        for i in range(len(self.ramos[0].barraPara.ramosJusante)):
            getDepth(self.ramos[0].barraPara.ramosJusante[i])

        mBranch = Deepest
        while mBranch is not None:
            mBranch.isMain = True
            isBigger = sum(1 for ramo in mBranch.barraPara.ramosJusante if ramo.accDB >= self.fjThreshould)
            if isBigger >= 2:
                mBranch.ForkJoin = True
            mBranch = mBranch.ramoMontante

    # FP DFS
    def FluxodePotencia(self):
        tIte = 100
        tDPQ = 1e-4
        
        for count in range(self.Npontos):
            nIte = 0
            maxDPQ = 1e-3

            # Construtores de tensão e corrente
            for i in range(len(self.barras)):
                self.barras[i].V = [0] * 3
                self.barras[i].I = [0] * 3

            for i in range(len(self.ramos)):
                self.ramos[i].J = [0] * 3

            # Definição dos parametros iniciais.
            for i in range(3):
                self.ramos[0].barraDe.V[i] = (self.vSE / math.sqrt(3) * cmath.rect(1, -i * 2 * cmath.pi / 3))
                self.ramos[0].barraDe.I[i] = (self.ramos[0].barraDe.S[i] / self.ramos[0].barraDe.V[i]).conjugate()

            self.ComT = datetime.now()
            while maxDPQ > tDPQ and nIte < tIte:
                self.Nucleosdisponiveis = self.Nucleos - 1
                mDPQ = [0.0]
                #mDPQ.append(0.0);
                for i in range(len(self.ramos[0].barraDe.ramosJusante)):                    
                    self.dfs(self.ramos[0].barraDe.ramosJusante[i], mDPQ)

                maxDPQ = mDPQ[0]
                nIte += 1

            self.ComT = datetime.now() - self.ComT
            self.dTbyRun.append(self.ComT.total_seconds() * 1000)

    # Busca em profundidade
    def dfs(self, ramo, mDPQ):

        for i in range(3):
            ramo.barraPara.V[i] = ramo.barraDe.V[i]

            for j in range(3):
                ramo.barraPara.V[i] -= ramo.zramo[i][j] * ramo.J[j]

            deltaS = ramo.barraPara.S[i] - ramo.barraPara.V[i] * ramo.barraPara.I[i].conjugate()           
            mDPQ[0] = max(mDPQ[0], max(abs(deltaS.real), abs(deltaS.imag)))
            ramo.barraPara.I[i] = (ramo.barraPara.S[i] / ramo.barraPara.V[i]).conjugate()

        for i in range(3):
            ramo.J[i] = ramo.barraPara.I[i]

        if ramo.ForkJoin and self.Nucleosdisponiveis > 0:
            self.Nucleosdisponiveis -= (len(ramo.barraPara.ramosJusante) - 1)
            
            ##asynchronous
            #loop = asyncio.get_event_loop()

            #looper = asyncio.create_task(*[self.dfs(ramo.barraPara.ramosJusante[i], mDPQ) for i in range(len(ramo.barraPara.ramosJusante))])
                               
            #loop.run_until_complete(asyncio.wait(looper)) 
            #loop.close()

            #multiprocessing
            #items = [(ramo.barraPara.ramosJusante[i], mDPQ) for i in range(len(ramo.barraPara.ramosJusante))]
            #with mp.Pool(len(ramo.barraPara.ramosJusante)) as pool:
            #    pool.starmap(self.dfs, items)
            #    pool.close()
            #    pool.join()

            #multithreading
            threads = []
            for i in range(len(ramo.barraPara.ramosJusante)):
                thread = threading.Thread(target=self.dfs, args = (ramo.barraPara.ramosJusante[i], mDPQ))
                thread.start()
                threads.append(thread)

            for thread in threads:
                thread.join()
           
            #concurrent
            #with cf.ThreadPoolExecutor(max_workers=len(ramo.barraPara.ramosJusante)) as executor:
            #    futures_DPQ = []
            #    for i in range(len(ramo.barraPara.ramosJusante)):
            #        futures_DPQ.append(executor.submit(self.dfs, ramo.barraPara.ramosJusante[i], mDPQ))
            #        for future in cf.as_completed(futures_DPQ):
            #            future.result()
               
            for i in range(len(ramo.barraPara.ramosJusante)):
                for k in range(3):
                    ramo.J[k] += ramo.barraPara.ramosJusante[i].J[k]
                
        else:
            for i in range(len(ramo.barraPara.ramosJusante)):
                self.dfs(ramo.barraPara.ramosJusante[i], mDPQ)

                for k in range(3):
                    ramo.J[k] += ramo.barraPara.ramosJusante[i].J[k]

    # Organizador de strings
    def centeredString(s, width):
        if len(s) >= width:
            return s
        num = (width - len(s)) // 2
        count = width - len(s) - num
        return ' ' * num + s + ' ' * count

    # Funçao de impressão dependente da parametrização pelo usuário
    def imprimirValores(self, _path, print_tensao, print_corrente, print_cuscom):
        # Ensure the output_path points directly to the file
        if not _path.endswith(".txt"):
            output_path = os.path.join(_path, "Resultados.txt")

        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(_path), exist_ok=True)

        with open(_path, "w") as f:
            if print_tensao == True:
                f.write(Rede.centeredString("Barras", 130) + "\n")
                f.write("{0}\t{1}\t{2}\n".format("Nº Barra", "Tensão em PU", "Tensão em V"))

                for i in range(len(self.barras)):
                    value = "{0}\t{1}\t{2}\t{3}\t{4}\t{5}\t{6}".format(
                        self.barras[i].Numero,
                        (abs(self.barras[i].V[0]) / self.vSE * math.sqrt(3.0)),
                        cmath.phase(self.barras[i].V[0]),
                        (abs(self.barras[i].V[1]) / self.vSE * math.sqrt(3.0)),
                        cmath.phase(self.barras[i].V[1]),
                        (abs(self.barras[i].V[2]) / self.vSE * math.sqrt(3.0)),
                        cmath.phase(self.barras[i].V[2])
                    )
                    f.write(value + "\n")

                f.write(
                    "----------------------------------------------------------------------------------------------------------------------------------\n")

            if print_corrente == True:
                f.write(Rede.centeredString("Ramos", 64) + "\n")
                f.write("{0}\t{1}\t{2}\n".format("Nº BarraDe", "Nº BarraPara", "Corrente em A"))

                for j in range(len(self.ramos)):
                    value = "{0}\t{1}\t{2}\t{3}\t{4}\t{5}\t{6}\t{7}".format(
                        self.ramos[j].barraDe.Numero,
                        self.ramos[j].barraPara.Numero,
                        abs(self.ramos[j].J[0]),
                        cmath.phase(self.ramos[j].J[0]),
                        abs(self.ramos[j].J[1]),
                        cmath.phase(self.ramos[j].J[1]),
                        abs(self.ramos[j].J[2]),
                        cmath.phase(self.ramos[j].J[2])
                    )
                    f.write(value + "\n")

                f.write(
                    "----------------------------------------------------------------------------------------------------------------------------------\n")

            if print_cuscom == True and self.GetTime:
                f.write("<<<TEMPO DE PROCESSAMENTO>>>\n")
                self.dTbyRun.pop(0)
                f.write("Tmédio = {0} ms\n".format(sum(self.dTbyRun) / len(self.dTbyRun)))
                for k in range(len(self.dTbyRun)):
                    f.write(str(self.dTbyRun[k]) + "\n")

    def FluxodePotenciaSequencial(self):
        tIte = 100
        tDPQ = 1e-4

        for count in range(self.Npontos):
            nIte = 0
            maxDPQ = 1e-3

            for i in range(len(self.barras)):
                self.barras[i].V = [0] * 3
                self.barras[i].I = [0] * 3

            for i in range(len(self.ramos)):
                self.ramos[i].J = [0] * 3

            for i in range(3):
                self.ramos[0].barraDe.V[i] = (self.vSE / math.sqrt(3) * cmath.rect(1, -i * 2 * cmath.pi / 3))
                self.ramos[0].barraDe.I[i] = (self.ramos[0].barraDe.S[i] / self.ramos[0].barraDe.V[i]).conjugate()

            start_time = time.time()
            while maxDPQ > tDPQ and nIte < tIte:
                maxDPQ = 0

                for k in range(len(self.ListaAdj)):
                    for i in range(3):
                        self.ListaAdj[k].barraPara.V[i] = self.ListaAdj[k].barraDe.V[i]
                        for j in range(3):
                            self.ListaAdj[k].barraPara.V[i] -= self.ListaAdj[k].zramo[i][j] * self.ListaAdj[k].J[j]

                        #deltaS = self.ramos[0].barraDe.I[i] = self.ramos[0].barraDe.S[i] / self.ramos[0].barraDe.V[i].conjugate()
                        deltaS = self.ListaAdj[k].barraPara.S[i] - self.ListaAdj[k].barraPara.V[i] * self.ListaAdj[k].barraPara.I[i].conjugate()
                        maxDPQ = max(maxDPQ, max(abs(deltaS.real), abs(deltaS.imag)))
                        self.ListaAdj[k].barraPara.I[i] = (self.ListaAdj[k].barraPara.S[i] / self.ListaAdj[k].barraPara.V[i]).conjugate()


                for k in range(len(self.ListaAdj) - 1, -1, -1):
                    for i in range(3):
                        self.ListaAdj[k].J[i] = self.ListaAdj[k].barraPara.I[i]

                    for i in range(len(self.ListaAdj[k].barraPara.ramosJusante)):
                        for l in range(3):
                            self.ListaAdj[k].J[l] += self.ListaAdj[k].barraPara.ramosJusante[i].J[l]

                nIte += 1                
            end_time = time.time()

            elapsed_time = (end_time - start_time) * 1e3; #in ms
            self.dTbyRun.append(elapsed_time)
