from multiprocessing import pool
import xml.etree.ElementTree as ET
import os
import time
from BModel import Rede

#Main
if __name__ == '__main__':
    print("<<Solucao do Fluxo de Potencias em Redes de Distribuicao>>")

    #Selector
    print( "Selecione o Sistema Teste:");
    sel = int(input( "1. 25b" + "\t"
            + "2. 49b" + "\t"
            + "3. 78b" + "\t"
            + "4. 106b" + "\t"
            + "5. 135b" + "\t"
            + "6. 269b" + "\t"
            + "7. 403b" + "\t"
            + "8. 538b" + "\t"
            + "9. 672b" + "\t"
            + "10. 806b \t"))
    nSys =  ["25b", "49b", "78b", "106b", "135b", "269b", "403b", "538b", "672b", "806b"]
    print("A sistema " + nSys[sel - 1] + " foi selecionada.\n")

    xdoc = ET.parse(os.path.join(os.path.dirname(__file__), "tDN_" + nSys[sel - 1] + ".xml"))

    rd = Rede()
    rd.lerRede(xdoc)


    print("Selecione a Quantidade de Execucoes do Algoritmo:");
    sel = int(input( "1. Dez" + "\t"
            + "2. Cem" + "\t"
            + "3. Mil" + "\t"
            + "4. Dez mil" + "\t"))
    qEx =  [10, 100, 1000, 10000]
    print("O algorimo sera executado " + str(qEx[sel - 1]) + " vezes.\n")
    rd.Npontos = int(qEx[sel - 1]) + 1

    print("Selecione o Tipo de Algoritmo:");
    sel = int(input( "1. Sequencial" + "\t"
            + "2. Recursivo" + "\t"))
    if sel == 1:
            print("Fluxo de potencia sequencial.\n")
            rd.FluxodePotenciaSequencial()
    else:
            print("Fluxo de potencia recursivo.\n")
            rd.Nucleos = int(input("Quantidade de nucleos disponiveis (entre 1 e 12): "))
            rd.FluxodePotencia()

    dt = float(sum(rd.dTbyRun)/rd.Npontos)
    print("\nTempo medio de execucao do Algoritmo: " + str(dt) + " ms")

    sel = input("\nImprimir o Arquivo de Resultados (s/n): ")
    if sel == "s" or sel == "S":
        print_tensao = True
        print_corrente = True
        print_cuscom = False
        rd.imprimirValores(os.path.join(os.path.dirname(__file__), "Resultados.txt"), print_tensao, print_corrente, print_cuscom)