#!/bin/bash

# Script para gestionar CID con Docker Compose

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

function show_menu() {
    echo -e "${GREEN}==================================${NC}"
    echo -e "${GREEN}     CID Docker Manager${NC}"
    echo -e "${GREEN}==================================${NC}"
    echo "1) Iniciar CID (backend + frontend)"
    echo "2) Detener CID"
    echo "3) Ver logs del backend"
    echo "4) Ver logs del frontend"
    echo "5) Ver logs de todo"
    echo "6) Reconstruir e iniciar"
    echo "7) Estado de los servicios"
    echo "8) Reiniciar backend"
    echo "9) Reiniciar frontend"
    echo "0) Salir"
    echo -e "${GREEN}==================================${NC}"
}

function start_services() {
    echo -e "${YELLOW}Iniciando servicios CID...${NC}"
    docker-compose up -d
    echo -e "${GREEN}✓ Servicios iniciados${NC}"
    echo ""
    echo -e "${GREEN}URLs disponibles:${NC}"
    echo "  - Backend API: http://10.1.5.133:8001"
    echo "  - Frontend UI: http://10.1.5.133:3000"
    echo "  - Health Check: http://10.1.5.133:8001/auth/health"
}

function stop_services() {
    echo -e "${YELLOW}Deteniendo servicios CID...${NC}"
    docker-compose down
    echo -e "${GREEN}✓ Servicios detenidos${NC}"
}

function show_backend_logs() {
    echo -e "${YELLOW}Mostrando logs del backend (Ctrl+C para salir)...${NC}"
    docker-compose logs -f cid-backend
}

function show_frontend_logs() {
    echo -e "${YELLOW}Mostrando logs del frontend (Ctrl+C para salir)...${NC}"
    docker-compose logs -f cid-frontend
}

function show_all_logs() {
    echo -e "${YELLOW}Mostrando todos los logs (Ctrl+C para salir)...${NC}"
    docker-compose logs -f
}

function rebuild_and_start() {
    echo -e "${YELLOW}Reconstruyendo e iniciando servicios...${NC}"
    docker-compose down
    docker-compose build --no-cache
    docker-compose up -d
    echo -e "${GREEN}✓ Servicios reconstruidos e iniciados${NC}"
}

function show_status() {
    echo -e "${YELLOW}Estado de los servicios:${NC}"
    docker-compose ps
    echo ""
    echo -e "${YELLOW}Verificando conectividad:${NC}"
    
    # Check backend
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/auth/health | grep -q "200"; then
        echo -e "${GREEN}✓ Backend API está funcionando${NC}"
    else
        echo -e "${RED}✗ Backend API no responde${NC}"
    fi
    
    # Check frontend
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 | grep -q "200\|304"; then
        echo -e "${GREEN}✓ Frontend está funcionando${NC}"
    else
        echo -e "${RED}✗ Frontend no responde${NC}"
    fi
}

function restart_backend() {
    echo -e "${YELLOW}Reiniciando backend...${NC}"
    docker-compose restart cid-backend
    echo -e "${GREEN}✓ Backend reiniciado${NC}"
}

function restart_frontend() {
    echo -e "${YELLOW}Reiniciando frontend...${NC}"
    docker-compose restart cid-frontend
    echo -e "${GREEN}✓ Frontend reiniciado${NC}"
}

# Main loop
while true; do
    show_menu
    read -p "Selecciona una opción: " option
    
    case $option in
        1)
            start_services
            ;;
        2)
            stop_services
            ;;
        3)
            show_backend_logs
            ;;
        4)
            show_frontend_logs
            ;;
        5)
            show_all_logs
            ;;
        6)
            rebuild_and_start
            ;;
        7)
            show_status
            ;;
        8)
            restart_backend
            ;;
        9)
            restart_frontend
            ;;
        0)
            echo -e "${GREEN}¡Hasta luego!${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}Opción inválida${NC}"
            ;;
    esac
    
    echo ""
    read -p "Presiona Enter para continuar..."
    clear
done