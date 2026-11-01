-- Esquema relacional (MySQL 8 / MariaDB) — LPS Eventos Científicos
-- Gerado a partir dos modelos SQLAlchemy de cada microservice (services/<svc>/model.py).
-- Cada microservice tem seu PRÓPRIO banco, por tenant: lps_<tenant>_<servico>.
-- As tabelas são criadas automaticamente na primeira execução; este script serve de documentação/criação manual.

-- ===================== users =====================
CREATE DATABASE IF NOT EXISTS `lps_sbes_2026_users` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `lps_sbes_2026_users`;
CREATE TABLE usuario (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	nome VARCHAR(120) NOT NULL, 
	email VARCHAR(160) NOT NULL, 
	senha_hash VARCHAR(255) NOT NULL, 
	papel VARCHAR(20) NOT NULL, 
	criado_em DATETIME NOT NULL DEFAULT (now()), 
	PRIMARY KEY (id)
);
CREATE TABLE historico_interacao (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	usuario_id INTEGER NOT NULL, 
	sessao_id INTEGER NOT NULL, 
	acao VARCHAR(10) NOT NULL, 
	criado_em DATETIME NOT NULL DEFAULT (now()), 
	PRIMARY KEY (id), 
	FOREIGN KEY(usuario_id) REFERENCES usuario (id) ON DELETE CASCADE
);
CREATE TABLE interesse (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	usuario_id INTEGER NOT NULL, 
	termo VARCHAR(80) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_interesse_usuario_termo UNIQUE (usuario_id, termo), 
	FOREIGN KEY(usuario_id) REFERENCES usuario (id) ON DELETE CASCADE
);

-- ===================== events =====================
CREATE DATABASE IF NOT EXISTS `lps_sbes_2026_events` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `lps_sbes_2026_events`;
CREATE TABLE tag (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	nome VARCHAR(80) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (nome)
);
CREATE TABLE trilha (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	nome VARCHAR(80) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (nome)
);
CREATE TABLE sessao (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	titulo VARCHAR(200) NOT NULL, 
	trilha_id INTEGER, 
	palestrante VARCHAR(120) NOT NULL, 
	dia DATE NOT NULL, 
	inicio TIME NOT NULL, 
	sala VARCHAR(60) NOT NULL, 
	tipo VARCHAR(30) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(trilha_id) REFERENCES trilha (id) ON DELETE SET NULL
);
CREATE TABLE sessao_tag (
	sessao_id INTEGER NOT NULL, 
	tag_id INTEGER NOT NULL, 
	PRIMARY KEY (sessao_id, tag_id), 
	FOREIGN KEY(sessao_id) REFERENCES sessao (id) ON DELETE CASCADE, 
	FOREIGN KEY(tag_id) REFERENCES tag (id) ON DELETE CASCADE
);

-- ===================== registration =====================
CREATE DATABASE IF NOT EXISTS `lps_sbes_2026_registration` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `lps_sbes_2026_registration`;
CREATE TABLE agenda_item (
	usuario_id INTEGER NOT NULL, 
	sessao_id INTEGER NOT NULL, 
	adicionado_em DATETIME NOT NULL DEFAULT (now()), 
	PRIMARY KEY (usuario_id, sessao_id)
);
CREATE TABLE inscricao (
	usuario_id INTEGER NOT NULL, 
	status VARCHAR(10) NOT NULL, 
	metodo VARCHAR(20) NOT NULL, 
	valor NUMERIC(10, 2) NOT NULL, 
	criado_em DATETIME NOT NULL DEFAULT (now()), 
	atualizado_em DATETIME NOT NULL DEFAULT (now()), 
	PRIMARY KEY (usuario_id)
);
CREATE TABLE pagamento (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	usuario_id INTEGER NOT NULL, 
	metodo VARCHAR(20) NOT NULL, 
	valor NUMERIC(10, 2) NOT NULL, 
	status VARCHAR(10) NOT NULL, 
	txid VARCHAR(40), 
	detalhes TEXT NOT NULL, 
	criado_em DATETIME NOT NULL DEFAULT (now()), 
	PRIMARY KEY (id), 
	FOREIGN KEY(usuario_id) REFERENCES inscricao (usuario_id) ON DELETE CASCADE
);

-- ===================== recommendation =====================
CREATE DATABASE IF NOT EXISTS `lps_sbes_2026_recommendation` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `lps_sbes_2026_recommendation`;
CREATE TABLE recomendacao (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	usuario_id INTEGER NOT NULL, 
	sessao_id INTEGER NOT NULL, 
	titulo_sessao VARCHAR(200) NOT NULL, 
	score FLOAT NOT NULL, 
	estrategia VARCHAR(30) NOT NULL, 
	motivo VARCHAR(300) NOT NULL, 
	gerado_em DATETIME NOT NULL DEFAULT (now()), 
	PRIMARY KEY (id)
);

-- ===================== submissions =====================
CREATE DATABASE IF NOT EXISTS `lps_sbes_2026_submissions` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `lps_sbes_2026_submissions`;
CREATE TABLE submissao (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	autor_id INTEGER NOT NULL, 
	titulo VARCHAR(250) NOT NULL, 
	resumo TEXT NOT NULL, 
	formato VARCHAR(20) NOT NULL, 
	status VARCHAR(15) NOT NULL, 
	criado_em DATETIME NOT NULL DEFAULT (now()), 
	PRIMARY KEY (id)
);
CREATE TABLE coautor (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	submissao_id INTEGER NOT NULL, 
	nome VARCHAR(120) NOT NULL, 
	ordem INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(submissao_id) REFERENCES submissao (id) ON DELETE CASCADE
);
CREATE TABLE palavra_chave (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	submissao_id INTEGER NOT NULL, 
	termo VARCHAR(60) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(submissao_id) REFERENCES submissao (id) ON DELETE CASCADE
);

-- ===================== reviews =====================
CREATE DATABASE IF NOT EXISTS `lps_sbes_2026_reviews` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `lps_sbes_2026_reviews`;
CREATE TABLE parecer (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	submissao_id INTEGER NOT NULL, 
	revisor_id INTEGER NOT NULL, 
	revisor_nome VARCHAR(120) NOT NULL, 
	nota SMALLINT NOT NULL, 
	comentario TEXT NOT NULL, 
	criado_em DATETIME NOT NULL DEFAULT (now()), 
	PRIMARY KEY (id), 
	CONSTRAINT uq_parecer_submissao_revisor UNIQUE (submissao_id, revisor_id)
);

-- ===================== certificates =====================
CREATE DATABASE IF NOT EXISTS `lps_sbes_2026_certificates` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `lps_sbes_2026_certificates`;
CREATE TABLE certificado (
	codigo VARCHAR(16) NOT NULL, 
	usuario_id INTEGER NOT NULL, 
	tipo VARCHAR(20) NOT NULL, 
	texto TEXT NOT NULL, 
	carga_horaria SMALLINT NOT NULL, 
	emitido_em DATETIME NOT NULL DEFAULT (now()), 
	PRIMARY KEY (codigo)
);

-- ===================== notifications =====================
CREATE DATABASE IF NOT EXISTS `lps_sbes_2026_notifications` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `lps_sbes_2026_notifications`;
CREATE TABLE email_enviado (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	destinatario VARCHAR(160) NOT NULL, 
	assunto VARCHAR(150) NOT NULL, 
	corpo TEXT NOT NULL, 
	enviado_em DATETIME NOT NULL DEFAULT (now()), 
	PRIMARY KEY (id)
);
CREATE TABLE evento_recebido (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	tipo VARCHAR(40) NOT NULL, 
	usuario_id INTEGER NOT NULL, 
	canais VARCHAR(60) NOT NULL, 
	criado_em DATETIME NOT NULL DEFAULT (now()), 
	PRIMARY KEY (id)
);
CREATE TABLE notificacao (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	usuario_id INTEGER NOT NULL, 
	assunto VARCHAR(150) NOT NULL, 
	mensagem TEXT NOT NULL, 
	lida BOOL NOT NULL, 
	criado_em DATETIME NOT NULL DEFAULT (now()), 
	PRIMARY KEY (id)
);

-- ===================== ai_agent =====================
CREATE DATABASE IF NOT EXISTS `lps_sbes_2026_ai_agent` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `lps_sbes_2026_ai_agent`;
CREATE TABLE conhecimento (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	usuario_id INTEGER NOT NULL, 
	chave VARCHAR(60) NOT NULL, 
	valor VARCHAR(500) NOT NULL, 
	atualizado_em DATETIME NOT NULL DEFAULT (now()), 
	PRIMARY KEY (id), 
	CONSTRAINT uq_conhecimento_usuario_chave UNIQUE (usuario_id, chave)
);
CREATE TABLE memoria_evento (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	usuario_id INTEGER NOT NULL, 
	papel VARCHAR(10) NOT NULL, 
	texto TEXT NOT NULL, 
	criado_em DATETIME NOT NULL DEFAULT (now()), 
	PRIMARY KEY (id)
);
CREATE TABLE registro_caixa_preta (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	requisicao_id VARCHAR(32) NOT NULL, 
	usuario_id INTEGER NOT NULL, 
	ordem INTEGER NOT NULL, 
	componente VARCHAR(60) NOT NULL, 
	entrada TEXT NOT NULL, 
	saida TEXT NOT NULL, 
	criado_em DATETIME NOT NULL DEFAULT (now()), 
	PRIMARY KEY (id)
);
