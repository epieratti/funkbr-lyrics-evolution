# Collector Notes - FunkBR Lyrics Evolution

## 1. **Seed Resolution**
O coletor de catálogo agora resolve os seeds de forma flexível, considerando a ordem a seguir:
1. **CLI**: Permite especificar um arquivo de seed diretamente ao executar o comando de coleta.
2. **Defaults do Repositório**: O coletor usa `seed/seeds.txt` se nenhum arquivo for especificado via CLI.
3. **Seeds Temporários para Testes**: Para testes, o coletor pode gerar uma lista temporária de seeds para uso em ambientes isolados.

**Fallback**: Caso o arquivo de seed não esteja presente ou seja inválido, o coletor agora lança um aviso claro no log e continua com a execução (para fins de depuração).

### Exemplos de Execução
```bash
# Usar seed padrão do repositório
python code/collect_spotify_catalog.py --snapshot test

# Especificar seed manualmente via CLI
python code/collect_spotify_catalog.py --snapshot test --seed custom_seed.txt
