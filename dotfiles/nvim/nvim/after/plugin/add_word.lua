function AddWordToDictionary()
    local word = vim.fn.expand("<cword>")
    local dict_path = "~/.config/nvim/dictionary/pt-BR.dic"
    local cmd = string.format("echo %s >> %s", word, dict_path)
    os.execute(cmd)
    print("Palavra adicionada ao dicionário: " .. word)
    -- Forçando o LSP a reconhecer o novo dicionário 
    vim.lsp.stop_client(vim.lsp.get_active_clients())
    vim.defer_fn(function() vim.cmd("LspRestart") end, 1)
end

local addWord = AddWordToDictionary
vim.keymap.set("n", "<leader>aw", addWord, { noremap = true, silent = true })
print('after/plugin/add_word.lua carregado com sucesso!')
