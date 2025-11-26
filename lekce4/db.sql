-- 1. Vytvoření databáze 'siem', pokud ještě neexistuje
CREATE DATABASE IF NOT EXISTS siem
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

-- 2. Přepnutí do nově vytvořené databáze
USE siem;

-- 3. Vytvoření tabulky 'hosts'
CREATE TABLE IF NOT EXISTS hosts (
    id INT AUTO_INCREMENT PRIMARY KEY, -- Unikátní identifikátor, zvyšuje se automaticky
    name VARCHAR(255) NOT NULL,        -- Název hosta (např. server-01), povinné pole
    company VARCHAR(255) NOT NULL,     -- Název společnosti, povinné pole
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP -- Volitelné: Čas vytvoření záznamu
) ENGINE=InnoDB;

-- Volitelné: Vložení testovacích dat (odkomentujte pro použití)
INSERT INTO hosts (name, company) VALUES ('firewall-main', 'Acme Corp');
INSERT INTO hosts (name, company) VALUES ('web-server-01', 'Omega s.r.o.');

