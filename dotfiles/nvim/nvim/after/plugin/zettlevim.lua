-- Author: Gabriel Góes Rocha de Lima
-- Email: gabrielgoes@usp.br
-- Date: 2024-02-08
-- Last Modified: 2024-02-08
-- Version: 0.1
-- License: GPL
-- Description: Pluggin para transformar o neovim em um zettelkasten machine
-------------------------------------------------------------------------------
local tempestade_path = os.getenv("NVIM_TEMPESTADE")
-- Tratar todos os arquivos de um diretório como Markdown mesmo sem a extensão
local function setMarkdonwFileType()
    -- Obtém o caminho completo do arquivo atual
    local current_path = vim.fn.expand("%:p")
    -- verifica se o caminho atual começa com tempestade_path
    if current_path:sub(1, #tempestade_path) == tempestade_path then
        -- Ajusta o filetype para markdow
        vim.bo.filetype = "markdown"
    end
end
-- Cria autocmd que chama setMarkdonwFileType para arquivos em tempestade_path
vim.api.nvim_create_autocmd({"BufRead", "BufNewFile"}, {
    pattern = "*",
    callback = setMarkdonwFileType,
    }
)
-- Transformando uma palavra é um título, Capitalize First Letter
local function capitalizeFirstLetter(str)
    return (str:gsub("^.", string.upper))
end
-------------------------------------------------------------------------------

---------------------- ZettleVimCreateBiderecionalLink-------------------------
-- Função para criar um link bidirecional entre dois arquivos
function ZettleVimCreateBiderecionalLink(word)
    -- Verifica se no arquivo atual possui um link para a palavra no formato "#palavra"
    local currentFileContent = vim.fn.readfile(vim.fn.expand("%:p"))
    local wordExists = false
    -- Verifica se a palavra já existe no arquivo
    for _, line in ipairs(currentFileContent) do
        if line:find("#" .. word) then
            print("Link para " .. word .. " já existe")
            wordExists = true
            break
        end
    end
    -- Se não houver, adiciona a palavra no topo do arquivo atual como um link
    if not wordExists then
        table.insert(currentFileContent, 4, "#" .. word)
        -- Grava o conteúdo atualizado no arquivo
        vim.fn.writefile(currentFileContent, vim.fn.expand("%:p"))
        print("Link para #" .. word .. " adicionado")
    end
end
-------------------- ZettleVimCreateorFind(word) ------------------------------
function ZettleVimCreateorFind(word)
    -- Verifica se a palavra é vazia
    if word == "" then
        print("Sem palavras, tsc tsc tsc ...")
        return
    end
    local filepath = tempestade_path .. word
    local tempCerebralPath = tempestade_path .. "tempestade cerebral"
    -- Verifica se o arquivo existe. Se não, cria o arquivo
    if vim.fn.filereadable(filepath) == 0 then
        local titulo = "# " .. capitalizeFirstLetter(word)
        local link_line_head = "---- links ---------------------------------------------------------------------"
        local link_line_tail = "--------------------------------------------------------------------------------"
        local arquivoCriador = vim.fn.expand("%:t:r")
        -- Cria o arquivo com título e pula linha, adiciona o link_line_head e link_line_tail
        vim.fn.writefile({titulo, '', link_line_head, '#' .. arquivoCriador, link_line_tail, ''}, filepath)
        -- Adiciona a palavra ao arquivo "tempestade cerebral" como um indice
        local tempCerebralContent  = vim.fn.readfile(tempCerebralPath)
        table.insert(tempCerebralContent,"    - #" ..  word)
        vim.fn.writefile(tempCerebralContent, tempCerebralPath)
        print(word .. " adicionado ao arquivo tempestade cerebral")
        -- Cria um link bidirecional no arquivo atual apara a palavra
        ZettleVimCreateBiderecionalLink(word)
    -- Se a palavra já existe, checa se o arquivo atual já possui um link para a palavra
    else
        ZettleVimCreateBiderecionalLink(word)
    end
        -- abre o arquivo existente
        vim.cmd('edit ' .. filepath)
end
-------------------------------------------------------------------------------
-- CreatorFind Visual Mode
vim.keymap.set("v", "gF", function()
    -- Yank a seleção do buffer no visual mode, e apenas a seleção ao registro 'a'
    vim.cmd("normal! \"ay")
    -- Imediatamente após o yan, obtém a seleção do registro 'a' e armazena na variável selection
    local selection = vim.fn.getreg("a")
    print("Seleção: " .. selection)
    -- Chama a função ZettleVimCreateorFind com a seleção
    ZettleVimCreateorFind(selection)
    -- limpa o registro 'a'
    vim.fn.setreg("a", "")
end, {noremap = true, silent = true})
-- CreatorFind Normal Mode
vim.keymap.set("n", "<leader>gg", function()
    print("Comando <leader>gg executado ...")
    local word = vim.fn.expand("<cword>")
    ZettleVimCreateorFind(word)
end, {noremap = true, silent = true})
print("ZettleVim carregado com sucesso")
