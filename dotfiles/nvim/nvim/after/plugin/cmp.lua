-- Autor: Gabriel Góes Rocha de Lima
-- after/plugin/cmp.lua
-- Last Change: 2024-02-05 00:48
-- Configurações do cmp
local cmp = require('cmp')
cmp.setup({
    snippet = {
        -- REQUIRED - you must specify a snippet engine
        expand = function(args)
            require('luasnip').lsp_expand(args.body)
        end,
    },
    window = {
        -- completion = cmp.config.window.bordered(),
        -- documentation = cmp.config.window.bordered(),
    },
    mapping = cmp.mapping.preset.insert({
        ['<C-b>'] = cmp.mapping.scroll_docs(-4),
        ['<C-f>'] = cmp.mapping.scroll_docs(4),
        ['<C-Space>'] = cmp.mapping.complete(),
        ['<C-e>'] = cmp.mapping.close(),
        ['<C-y>'] = cmp.mapping.confirm({ select = true }),
    }),
    sources = cmp.config.sources({
        { name = 'nvim_lsp' },
        { name = 'luasnip' },
        { name = 'buffer' },
        { name = 'path' },
        { name = 'cmdline' },
    })
})
-- Set configuration for spcific filetypes
cmp.setup.filetype('gitcommit', {
    sources = cmp.config.sources({
        { name = 'git' },
    }, {
        { name = 'buffer' },
    })
})
-- Use buffer for '/' and '?' (if you enabled 'native_menu', this wont work)
cmp.setup.cmdline({ '/', '?' }, {
    mapping = cmp.mapping.preset.cmdline(),
    sources = {
        { name = 'buffer' }
    }
})
-- use cmdline & path source for ':' (if you enabled 'native_menu', this wont work)
cmp.setup.cmdline(':', {
    mapping = cmp.mapping.preset.cmdline(),
    sources = cmp.config.sources({
        { name = 'path' }
    }, {
        { name = 'cmdline' },
    })
})
local capabilities = require('cmp_nvim_lsp').default_capabilities()
-- Replace <pylsp> with each lsp server you've enabled.
require('lspconfig').pylsp.setup {
    capabilities = capabilities
}
require('lspconfig').lua_ls.setup {
    capabilities = capabilities
}
print("CMP carregado com sucesso!")
