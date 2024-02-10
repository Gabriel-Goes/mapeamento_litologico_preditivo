-- Configurações do Vim Fugitive
vim.keymap.set("n","<leader>gs", vim.cmd.Git)

-- Função para adicionar todos os arquivos do diretório atual ao git
function vim.cmd.GitAddLocal()
    -- Checa o diretório atual
    -- Se não estiver no diretório do arquivo do buffer, retorna
    if vim.fn.expand("%:p:h") ~= vim.fn.getcwd() then
        -- printa o diretorio atual e diz que apenas ele foi add
        print("Apenas o diretório atual foi adicionado ao git")
        vim.cmd("Git add .")
        return
    -- Se estiver, checa se o diretório é um repositório git
    -- Se não for, retorna
    elseif vim.fn.system("git rev-parse --is-inside-work-tree") == 1 then
        return
    -- Se for, checa se o diretório está limpo
    -- Se estiver, retorna
    elseif vim.fn.system("git diff --quiet") == 1 then
        return
    -- Se não estiver, adiciona todos os arquivos
    else
        vim.cmd("Git add .")
    end
end

vim.keymap.set("n","<leader>gA", vim.cmd.GitAddLocal)
vim.keymap.set("n","<leader>gc", vim.cmd.GitCommit)

